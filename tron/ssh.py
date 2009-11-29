import os
import struct
import logging

from twisted.internet import protocol, reactor, defer

from twisted.conch import error
from twisted.conch.ssh import channel, common
from twisted.conch.ssh import connection
from twisted.conch.ssh import keys, userauth, agent
from twisted.conch.ssh import transport
from twisted.conch.client import default, options
from twisted.python import log

log = logging.getLogger('tron.ssh')

class ClientTransport(transport.SSHClientTransport):
    connection_defer = None
    def verifyHostKey(self, pubKey, fingerprint):
        return defer.succeed(1)

    def connectionSecure(self):
        conn = ClientConnection()
        conn.service_defer = defer.Deferred()

        self.connection_defer.callback(conn)
        
        self.requestService(default.SSHUserAuthClient(os.getlogin(), options.ConchOptions(), conn))

class ClientConnection(connection.SSHConnection):
    service_defer = None
    def serviceStarted(self):
        self.service_defer.callback(self)
        #self.openChannel(CatChannel(conn=self))

class ExecChannel(channel.SSHChannel):
    name = 'session'
    exit_defer = None
    command = None
    exit_status = None
    data = None

    def channelOpen(self, data):
        # env = common.NS('TEST_ENV') + common.NS("hello")
        # env setting doesn't appear to work. We get a "channel request failed"
        # self.conn.sendRequest(self, 'env', env, wantReply=True).addCallback(self._cbEnvSendRequest)
        
        self.data = []
        self.conn.sendRequest(self, 'exec', common.NS(self.command), wantReply=True).addCallback(self._cbExecSendRequest)

    # def _cbEnvSendRequest(self, ignored):
    #     self.conn.sendEOF(self)
    # 
    #     self.conn.sendRequest(self, 'exec', common.NS('env'), wantReply=True).addCallback(self._cbExecSendRequest)

    def _cbExecSendRequest(self, ignored):
        #self.write('This data will be echoed back to us by "cat."\r\n')
        self.conn.sendEOF(self)

    def request_exit_status(self, data):
        # exit status is a 32-bit unsigned int in network byte format
        status = struct.unpack_from(">L", data, 0)[0]

        log.info("Received exit status request: %d", status)
        self.exit_status = status
        self.exit_defer.callback(self)
        return True

    def dataReceived(self, data):
        self.data.append(data)

    def getStdout(self):
        return "".join(self.data)

    def closed(self):
        self.loseConnection()
