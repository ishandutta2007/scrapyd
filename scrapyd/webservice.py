from __future__ import annotations

import functools
import json
import os
import sys
import traceback
import uuid
import zipfile
from collections import defaultdict
from copy import copy
from io import BytesIO
from subprocess import PIPE, Popen
from typing import ClassVar

from twisted.python import log
from twisted.web import error, http, resource

from scrapyd.exceptions import EggNotFoundError, ProjectNotFoundError, RunnerError
from scrapyd.utils import native_stringify_dict


def param(
    decoded: str,
    *,
    dest: str | None = None,
    required: bool = True,
    default=None,
    multiple: bool = False,
    type=str,  # noqa: A002 like Click
):
    encoded = decoded.encode()
    if dest is None:
        dest = decoded
    if callable(default):
        default = default()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, txrequest, *args, **kwargs):
            if encoded not in txrequest.args:
                if required:
                    raise error.Error(code=http.OK, message=b"'%b' parameter is required" % encoded)

                value = default
            else:
                values = (value.decode() if type is str else type(value) for value in txrequest.args.pop(encoded))
                try:
                    value = list(values) if multiple else next(values)
                except (UnicodeDecodeError, ValueError) as e:
                    raise error.Error(code=http.OK, message=b"%b is invalid: %b" % (encoded, str(e).encode())) from e

            kwargs[dest] = value

            return func(self, txrequest, *args, **kwargs)

        return wrapper

    return decorator


class SpiderList:
    cache: ClassVar = defaultdict(dict)

    def get(self, project, version, *, runner):
        """Return the ``scrapy list`` output for the project and version, using a cache if possible."""
        try:
            return self.cache[project][version]
        except KeyError:
            return self.set(project, version, runner=runner)

    def set(self, project, version, *, runner):
        """Calculate, cache and return the ``scrapy list`` output for the project and version, bypassing the cache."""

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "UTF-8"
        env["SCRAPY_PROJECT"] = project
        # If the version is not provided, then the runner uses the default version, determined by egg storage.
        if version:
            env["SCRAPYD_EGG_VERSION"] = version

        args = [sys.executable, "-m", runner, "list", "-s", "LOG_STDOUT=0"]
        process = Popen(args, stdout=PIPE, stderr=PIPE, env=env)
        stdout, stderr = process.communicate()
        if process.returncode:
            raise RunnerError((stderr or stdout or b"").decode())

        spiders = stdout.decode().splitlines()

        # Note: If the cache is empty, that doesn't mean that this is the project's only version; it simply means that
        # this is the first version called in this Scrapyd process.

        # Evict the return value of version=None calls, since we can't determine whether this version is the default
        # version (in which case we would overwrite it) or not (in which case we would keep it).
        self.cache[project].pop(None, None)
        self.cache[project][version] = spiders
        return spiders

    def delete(self, project, version=None):
        if version is None:
            self.cache.pop(project, None)
        else:
            # Evict the return value of version=None calls, since we can't determine whether this version is the
            # default version (in which case we would pop it) or not (in which case we would keep it).
            self.cache[project].pop(None, None)
            self.cache[project].pop(version, None)


spider_list = SpiderList()


# WebserviceResource
class WsResource(resource.Resource):
    json_encoder = json.JSONEncoder()

    def __init__(self, root):
        super().__init__()
        self.root = root

    def render(self, txrequest):
        try:
            obj = super().render(txrequest)
        except Exception as e:  # noqa: BLE001
            log.err()

            if isinstance(e, error.Error):
                txrequest.setResponseCode(int(e.status))

            if self.root.debug:
                return traceback.format_exc().encode()

            message = e.message.decode() if isinstance(e, error.Error) else f"{type(e).__name__}: {e}"
            obj = {"node_name": self.root.nodename, "status": "error", "message": message}

        content = b"" if obj is None else self.json_encoder.encode(obj).encode() + b"\n"
        txrequest.setHeader("Content-Type", "application/json")
        txrequest.setHeader("Access-Control-Allow-Origin", "*")
        txrequest.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE")
        txrequest.setHeader("Access-Control-Allow-Headers", " X-Requested-With")
        txrequest.setHeader("Content-Length", str(len(content)))
        return content

    def render_OPTIONS(self, txrequest):
        methods = ["OPTIONS", "HEAD"]
        if hasattr(self, "render_GET"):
            methods.append("GET")
        if hasattr(self, "render_POST"):
            methods.append("POST")
        txrequest.setHeader("Allow", ", ".join(methods))
        txrequest.setResponseCode(http.NO_CONTENT)


class DaemonStatus(WsResource):
    def render_GET(self, txrequest):
        pending = sum(queue.count() for queue in self.root.scheduler.queues.values())
        running = len(self.root.launcher.processes)
        finished = len(self.root.launcher.finished)

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished,
        }


class Schedule(WsResource):
    @param("project")
    @param("spider")
    @param("_version", dest="version", required=False, default=None)
    # See https://github.com/scrapy/scrapyd/pull/215
    @param("jobid", required=False, default=lambda: uuid.uuid1().hex)
    @param("priority", required=False, default=0, type=float)
    @param("setting", required=False, default=list, multiple=True)
    def render_POST(self, txrequest, project, spider, version, jobid, priority, setting):
        if project not in self.root.scheduler.queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        if version and self.root.eggstorage.get(project, version) == (None, None):
            raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode())

        spiders = spider_list.get(project, version, runner=self.root.runner)
        if spider not in spiders:
            raise error.Error(code=http.OK, message=b"spider '%b' not found" % spider.encode())

        spider_arguments = {k: v[0] for k, v in native_stringify_dict(copy(txrequest.args)).items()}

        self.root.scheduler.schedule(
            project,
            spider,
            priority=priority,
            settings=dict(s.split("=", 1) for s in setting),
            version=version,
            _job=jobid,
            **spider_arguments,
        )
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}


class Cancel(WsResource):
    @param("project")
    @param("job")
    # Instead of os.name, use sys.platform, which disambiguates Cygwin, which implements SIGINT not SIGBREAK.
    # https://cygwin.com/cygwin-ug-net/kill.html
    # https://github.com/scrapy/scrapy/blob/06f9c28/tests/test_crawler.py#L886
    @param("signal", required=False, default="INT" if sys.platform != "win32" else "BREAK")
    def render_POST(self, txrequest, project, job, signal):
        if project not in self.root.scheduler.queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        prevstate = None

        if self.root.scheduler.queues[project].remove(lambda message: message["_job"] == job):
            prevstate = "pending"

        for process in self.root.launcher.processes.values():
            if process.project == project and process.job == job:
                process.transport.signalProcess(signal)
                prevstate = "running"

        return {"node_name": self.root.nodename, "status": "ok", "prevstate": prevstate}


class AddVersion(WsResource):
    @param("project")
    @param("version")
    @param("egg", type=bytes)
    def render_POST(self, txrequest, project, version, egg):
        if not zipfile.is_zipfile(BytesIO(egg)):
            raise error.Error(
                code=http.OK, message=b"egg is not a ZIP file (if using curl, use egg=@path not egg=path)"
            )

        self.root.eggstorage.put(BytesIO(egg), project, version)
        self.root.update_projects()

        spiders = spider_list.set(project, version, runner=self.root.runner)

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "project": project,
            "version": version,
            "spiders": len(spiders),
        }


class ListProjects(WsResource):
    def render_GET(self, txrequest):
        projects = self.root.scheduler.list_projects()
        return {"node_name": self.root.nodename, "status": "ok", "projects": projects}


class ListVersions(WsResource):
    @param("project")
    def render_GET(self, txrequest, project):
        versions = self.root.eggstorage.list(project)
        return {"node_name": self.root.nodename, "status": "ok", "versions": versions}


class ListSpiders(WsResource):
    @param("project")
    @param("_version", dest="version", required=False, default=None)
    def render_GET(self, txrequest, project, version):
        if project not in self.root.scheduler.queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        if version and self.root.eggstorage.get(project, version) == (None, None):
            raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode())

        spiders = spider_list.get(project, version, runner=self.root.runner)

        return {"node_name": self.root.nodename, "status": "ok", "spiders": spiders}


class Status(WsResource):
    @param("job")
    @param("project", required=False)
    def render_GET(self, txrequest, job, project):
        queues = self.root.scheduler.queues
        if project is not None and project not in queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        result = {"node_name": self.root.nodename, "status": "ok", "currstate": None}

        for finished in self.root.launcher.finished:
            if (project is None or finished.project == project) and finished.job == job:
                result["currstate"] = "finished"
                return result

        for process in self.root.launcher.processes.values():
            if (project is None or process.project == project) and process.job == job:
                result["currstate"] = "running"
                return result

        for queue_name in queues if project is None else [project]:
            for message in queues[queue_name].list():
                if message["_job"] == job:
                    result["currstate"] = "pending"
                    return result

        return result


class ListJobs(WsResource):
    @param("project", required=False)
    def render_GET(self, txrequest, project):
        queues = self.root.scheduler.queues
        if project is not None and project not in queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "pending": [
                {"project": queue_name, "spider": message["name"], "id": message["_job"]}
                for queue_name in (queues if project is None else [project])
                for message in queues[queue_name].list()
            ],
            "running": [
                process.asdict()
                for process in self.root.launcher.processes.values()
                if project is None or process.project == project
            ],
            "finished": [
                finished.asdict()
                for finished in self.root.launcher.finished
                if project is None or finished.project == project
            ],
        }


class DeleteProject(WsResource):
    @param("project")
    def render_POST(self, txrequest, project):
        self._delete_version(project)
        spider_list.delete(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        try:
            self.root.eggstorage.delete(project, version)
        except ProjectNotFoundError as e:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode()) from e
        except EggNotFoundError as e:
            raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode()) from e
        else:
            self.root.update_projects()


class DeleteVersion(DeleteProject):
    @param("project")
    @param("version")
    def render_POST(self, txrequest, project, version):
        self._delete_version(project, version)
        spider_list.delete(project, version)
        return {"node_name": self.root.nodename, "status": "ok"}
