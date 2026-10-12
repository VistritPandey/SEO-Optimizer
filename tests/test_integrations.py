import io
import json
import tarfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from seo_optimizer.application_models import FileChange, ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.crawler import CrawlError, Crawler
from seo_optimizer.execution import apply_changes, run_git
from seo_optimizer.github import GitHubClient
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password
from seo_optimizer.worker import Worker


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(['127.0.0.1'])
def test_real_git_http_worker_fix_merge_and_idempotence(tmp_path):
    repository=tmp_path/'repository';(repository/'web').mkdir(parents=True)
    page=repository/'web/index.html'
    page.write_text('<html><head><meta name="description" content="Actual guide"></head><body><h1>Actual guide</h1></body></html>')
    run_git(repository,'init','-b','main');run_git(repository,'add','web/index.html')
    run_git(repository,'-c','user.name=Fixture','-c','user.email=fixture@localhost','-c','commit.gpgsign=false','commit','-m','Add page')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(repository/'web')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    settings=Settings(data_dir=tmp_path/'data',database_url=f'sqlite:///{tmp_path}/db.sqlite',secret_key='fixture-secret',allowed_repo_roots=(tmp_path,))
    settings.data_dir.mkdir()
    store=Store(settings)
    user,_=store.create_user('fixture@example.test',hash_password('fixture-password-123'))
    spec=ProjectSpec.model_validate({'name':'Actual guide','website_url':f'http://127.0.0.1:{server.server_port}/','local_path':str(repository),'allowed_paths':['web']})
    project=store.create_project(user.id,ProjectCreate(spec=spec))
    service=Worker(store,settings)
    try:
        original=run_git(repository,'rev-parse','HEAD')
        assert service.tick()
        job=store.jobs(user.id)[0]
        assert job.status=='complete',job.result
        assert job.result['verified_fixes']==1
        assert '<title>Actual guide</title>' in page.read_text()
        assert run_git(repository,'rev-parse','HEAD')!=original
        assert not run_git(repository,'status','--porcelain')
        assert not service.tick()
        assert not any(item.active for item in store.findings(user.id,project.id) if item.details['check_id']=='tech.title')
        store.enqueue(user.id,project.id,'audit','again',{})
        assert service.tick()
        assert store.jobs(user.id)[0].result.get('verified_fixes',0)==0
        assert run_git(repository,'rev-list','--count','HEAD')=='2'
    finally:
        server.shutdown();server.server_close();store.engine.dispose()


def test_patch_policy_rejects_escape_ambiguous_context_and_body_edits(tmp_path):
    (tmp_path/'web').mkdir();(tmp_path/'web/index.html').write_text('<head></head><body>hello hello</body>')
    spec=ProjectSpec.model_validate({'name':'Fixture','website_url':'https://example.test/','allowed_paths':['web']})
    def change(path,before,after):return FileChange(path=path,before=before,after=after,reason='Fix',check_id='tech.title',evidence_ids=['page'])
    with pytest.raises(ValueError,match='scope'):apply_changes(tmp_path,spec,[change('../outside','hello','bye')],{'page'},{'tech.title'})
    with pytest.raises(ValueError,match='ambiguous'):apply_changes(tmp_path,spec,[change('web/index.html','hello','bye')],{'page'},{'tech.title'})
    with pytest.raises(ValueError,match='metadata'):apply_changes(tmp_path,spec,[change('web/index.html','<body>','<body>changed')],{'page'},{'tech.title'})


def test_ssrf_private_and_off_origin_rejected(monkeypatch):
    monkeypatch.setattr('socket.getaddrinfo',lambda *args:[(2,1,6,'',('169.254.169.254',80))])
    crawler=Crawler('https://example.test/')
    with pytest.raises(CrawlError,match='restricted'):crawler.check_url('https://example.test/')
    with pytest.raises(CrawlError,match='outside'):crawler.check_url('http://another.test/')
    crawler.close()


def test_github_multi_file_publication_single_file_commits_and_required_checks():
    calls=[];commits=[]
    def transport(request):
        path=request.url.path;body=json.loads(request.content) if request.content else {};calls.append((request.method,path,body))
        if path.endswith('/pulls') and request.method=='GET':return httpx.Response(200,json=[])
        if '/git/ref/heads/' in path:return httpx.Response(200,json={'object':{'sha':'base'}})
        if path.endswith('/git/commits/base'):return httpx.Response(200,json={'tree':{'sha':'tree0'}})
        if path.endswith('/git/blobs'):return httpx.Response(201,json={'sha':'blob'})
        if path.endswith('/git/trees'):
            assert len(body['tree'])==1
            return httpx.Response(201,json={'sha':'tree'+str(len(commits)+1)})
        if path.endswith('/git/commits'):
            commits.append(body);return httpx.Response(201,json={'sha':'commit'+str(len(commits))})
        if path.endswith('/git/refs'):return httpx.Response(201,json={})
        if path.endswith('/pulls'):return httpx.Response(201,json={'number':1,'html_url':'https://github.com/owner/site/pull/1'})
        if path.endswith('/status'):return httpx.Response(200,json={'statuses':[]})
        if path.endswith('/check-runs'):return httpx.Response(200,json={'total_count':1,'check_runs':[{'name':'build','status':'completed','conclusion':'success'}]})
        if path.endswith('/merge'):return httpx.Response(200,json={'merged':True,'sha':'merged'})
        raise AssertionError(path)
    github=GitHubClient(ProjectSecrets(github_token='fixture'),httpx.Client(transport=httpx.MockTransport(transport)))
    pr=github.create_pr('owner/site','main','base','job-id',{'web/a.html':'A','web/b.html':'B'},'Verified metadata changes')
    assert len(commits)==2 and commits[0]['parents']==['base'] and commits[1]['parents']==['commit1']
    assert pr['head_sha']=='commit2'
    assert github.checks_ready('owner/site',pr['head_sha'],['build'])=='ready'
    assert github.checks_ready('owner/site',pr['head_sha'],['missing-check'])=='pending'
    assert github.merge('owner/site',1,pr['head_sha'])['merged']


def test_github_existing_job_pr_is_reused_without_writes():
    def transport(request):
        assert request.method=='GET'
        return httpx.Response(200,json=[{'state':'open','number':3,'html_url':'https://github.com/owner/site/pull/3','head':{'sha':'existing'}}])
    github=GitHubClient(ProjectSecrets(github_token='fixture'),httpx.Client(transport=httpx.MockTransport(transport)))
    assert github.create_pr('owner/site','main','base','id',{'web/a.html':'A'},'Fix')['number']==3


def test_archive_symlink_cannot_escape(tmp_path):
    content=io.BytesIO()
    with tarfile.open(fileobj=content,mode='w:gz') as archive:
        member=tarfile.TarInfo('repo-root/web/link');member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd';archive.addfile(member)
    github=GitHubClient(ProjectSecrets(github_token='fixture'),httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=content.getvalue()))))
    with pytest.raises(ValueError,match='Unsafe'):github.checkout('owner/site','base',tmp_path/'checkout')
