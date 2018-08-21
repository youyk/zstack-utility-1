import traceback

from kvmagent import kvmagent
from zstacklib.utils import jsonobject
from zstacklib.utils import linux
from zstacklib.utils import log
from zstacklib.utils import shell
from zstacklib.utils import http

logger = log.get_logger(__name__)

class AgentRsp(object):
    def __init__(self):
        self.success = True
        self.error = None

class VMwareV2VConverter(kvmagent.KvmAgent):
    INIT_PATH = "/vmware_v2v_converter/init"
    CONVERT_PATH = "/vmware_v2v_converter/convert"
    CLEAN_PATH = "/vmware_v2v_converter/clean"
    
    def start(self):
        http_server = kvmagent.get_http_server()
        http_server.register_sync_uri(self.INIT_PATH, self.init)
        http_server.register_sync_uri(self.CONVERT_PATH, self.convert)
        http_server.register_sync_uri(self.CLEAN_PATH, self.clean)

    @in_bash
    @kvmagent.replyerror
    def init(self, cmd):
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = kvmagent.AgentResponse()
        cmdstr = 'which docker || yum --disablerepo=* --enablerepo=%s install docker' % cmd.zstackRepo
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to install docker in conversion host"
            return jsonobject.dumps(rsp)

        cmdstr = 'systemctl start docker && docker history virt-v2v'
        if (shell.run()) == 0:
            return jsonobject.dumps(rsp)

        cmdstr = 'mkdir -p %s && cd %s && wget -c %s -O virt_v2v_image.tgz && tar xvf virt_v2v_image.tgz' % (cmd.storagePath, cmd.storagePath, cmd.v2vImageUrl)
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to download virt_v2v_image.tgz from management node to v2v conversion host[uuid:%s]" % cmd.hostUuid
            return jsonobject.dumps(rsp)

        cmdstr = 'systemctl start docker && cat %s/virt_v2v_image.tar | docker import - virt-v2v && rm -f %s/virt_v2v_image*'
        if shell.run(cmdstr) != 0:
            rsp.success = False
            rsp.error = "failed to import virt_v2v_image to docker in v2v conversion host[uuid:%s]" % cmd.hostUuid
            return jsonobject.dumps(rsp)

        return jsonobject.dumps(rsp)

    @in_bash
    @kvmagent.replyerror
    def convert(self, cmd):
        rsp = kvmagent.AgentResponse()
        return jsonobject.dumps(rsp)

    @in_bash
    @kvmagent.replyerror
    def clean(self, cmd):
        rsp = kvmagent.AgentResponse()
        return jsonobject.dumps(rsp)
