# coding=utf-8
'''

@author: mingjian.deng
'''
import os.path
import traceback

import zstacklib.utils.uuidhelper as uuidhelper
from kvmagent import kvmagent
from kvmagent.plugins.imagestore import ImageStoreClient
from zstacklib.utils import http
from zstacklib.utils import jsonobject
from zstacklib.utils import linux
from zstacklib.utils import log
from zstacklib.utils import shell
from zstacklib.utils.bash import *

logger = log.get_logger(__name__)

tdcversion = 1

class AliyunEbsStoragePlugin(kvmagent.KvmAgent):
    INSTALL_TDC_PATH = "/aliyun/ebs/primarystorage/installtdc"
    DETACH_VOLUME_PATH = "/aliyun/ebs/primarystorage/detachvolume"

    def start(self):
        http_server = kvmagent.get_http_server()
        http_server.register_async_uri(self.INSTALL_TDC_PATH, self.installtdc)
        http_server.register_async_uri(self.DETACH_VOLUME_PATH, self.detachvolume)

        self.imagestore_client = ImageStoreClient()

    def stop(self):
        pass

    @kvmagent.replyerror
    def echo(self, req):
        logger.debug('get echoed')
        return ''

    @kvmagent.replyerror
    def installtdc(self, req):
        logger.debug('install tdc pkg')
        rsp = kvmagent.AgentResponse()
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        if cmd.version != tdcversion:
            rsp.error = "no matched tdc version found, agent need version %d" % tdcversion
        else:
            s = shell.ShellCmd("/opt/tdc/tdc_admin gtv")
            s(False)
            if s.return_code == 0:
                return jsonobject.dumps(rsp)
            yum_cmd = "yum --enablerepo=zstack-mn,qemu-kvm-ev-mn clean metadata"
            shell.call(yum_cmd)
            yum_cmd = "yum --disablerepo=* --enablerepo=zstack-mn,qemu-kvm-ev-mn install -y kernel-devel-3.10.0-693.11.1.el7.x86_64"
            shell.call(yum_cmd)
            yum_cmd = "yum --disablerepo=* --enablerepo=zstack-mn,qemu-kvm-ev-mn install -y tdc-unified-8.2.0.release.el5.x86_64"
            shell.call(yum_cmd)
            linux.mkdir("/apsara", 0755)
            shell.call("service tdc start")
            s = shell.ShellCmd("/opt/tdc/tdc_admin lsi")
            s(False)
            if s.return_code != 0:
                rsp.success = False
                rsp.error = "tdc_admin lsi failed: %s" % s.stderr

        return jsonobject.dumps(rsp)

    @kvmagent.replyerror
    def detachvolume(self, req):
        cmd = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug('detach volume %s' % cmd.volumeId)
        rsp = kvmagent.AgentResponse()
        s = shell.ShellCmd("/opt/tdc/tdc_admin destroy-vrbd --device_id=%d" % cmd.volumeId)
        s(False)
        if s.return_code != 0:
            rsp.success = False
            rsp.error = "detach volume failed: %s" % s.stderr

        return jsonobject.dumps(rsp)