import traceback

from kvmagent import kvmagent
from zstacklib.utils import jsonobject
from zstacklib.utils import linux
from zstacklib.utils import log
from zstacklib.utils import shell
from zstacklib.utils import http
from zstacklib.utils.bash import in_bash

logger = log.get_logger(__name__)

class AgentRsp(object):
    def __init__(self):
        self.success = True
        self.error = None

class VMwareV2VPlugin(kvmagent.KvmAgent):
    INIT_PATH = "/vmwarev2v/conversionhost/init"
    CONVERT_PATH = "/vmwarev2v/conversionhost/convert"
    CLEAN_PATH = "/vmwarev2v/conversionhost/clean"
    
    def start(self):
        http_server = kvmagent.get_http_server()
        http_server.register_async_uri(self.INIT_PATH, self.init)
        http_server.register_async_uri(self.CONVERT_PATH, self.convert)
        http_server.register_async_uri(self.CLEAN_PATH, self.clean)

    def stop(self):
        pass

    @in_bash
    @kvmagent.replyerror
    def init(self, req):
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = kvmagent.AgentResponse()
        cmdstr = 'which docker || yum --disablerepo=* --enablerepo={} install docker'.format(cmd.zstackRepo)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to install docker in conversion host"
            return jsonobject.dumps(rsp)

        cmdstr = 'systemctl start docker && docker history zs_virt_v2v'
        if (shell.run(cmdstr)) == 0:
            return jsonobject.dumps(rsp)

        cmdstr = 'mkdir -p {0} && cd {0} && wget -c {1} -O virt_v2v_image.tgz && tar xvf virt_v2v_image.tgz'.format(cmd.storagePath, cmd.v2vImageUrl)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to download virt_v2v_image.tgz from management node to v2v conversion host"
            return jsonobject.dumps(rsp)

        cmdstr = 'systemctl start docker && docker load < {0}/virt_v2v_image.tar && rm -f {0}/virt_v2v_image*'.format(cmd.storagePath)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to import virt_v2v_image to docker in v2v conversion host"
            return jsonobject.dumps(rsp)

        cmdstr = 'cd /usr/local/zstack && wget -c {} -O zstack-windows-virtio-driver.iso'.format(cmd.virtioDriverUrl)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to download zstack-windows-virtio-driver.iso from management node to v2v conversion host"
            return jsonobject.dumps(rsp)

        return jsonobject.dumps(rsp)

    @in_bash
    @kvmagent.replyerror
    def convert(self, req):
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = kvmagent.AgentResponse()
        storagePath = '{}/{}'.format(cmd.storagePath, cmd.dstVmUuid)
        cmdstr = "mkdir -p {0} && echo '{1}' > {0}/passwd".format(storagePath, cmd.vCenterPassword)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to create storagePath {} in v2v conversion host[hostUuid:{}]".format(storagePath, cmd.hostUuid)
            return jsonobject.dumps(rsp)

        virt_v2v_cmd = 'virt-v2v -ic vpx://{0}?no_verify=1 "{1}" -o local -os {2} --password-file {2}/passwd -of qcow2 --compress > {2}/virt_v2v_log 2>&1'.format(cmd.srcVmUri, cmd.srcVmName, storagePath)
        docker_run_cmd = 'docker run --rm -v /usr/local/zstack:/usr/local/zstack -v {0}:{0} --env VIRTIO_WIN=/usr/local/zstack/zstack-windows-virtio-driver.iso zs_virt_v2v {1}'.format(cmd.storagePath, virt_v2v_cmd)
        if shell.run(docker_run_cmd) != 0:
            rsp.success = False
            rsp.error = "failed to run virt-v2v command: " + docker_run_cmd
            return jsonobject.dumps(rsp)

        return jsonobject.dumps(rsp)

    @in_bash
    @kvmagent.replyerror
    def clean(self, req):
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = kvmagent.AgentResponse()
        if not cmd.dstVmUuid:
            cleanUpPath = cmd.storagePath
        else:
            cleanUpPath = '{}/{}'.format(cmd.storagePath, cmd.dstVmUuid)
        cmdstr = "/bin/rm -rf " + cleanUpPath
        shell.run(cmdstr)
        return jsonobject.dumps(rsp)
