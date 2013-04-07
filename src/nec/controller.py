'''
Created on Dec 23, 2009

@author: chris
'''

from nec.common.config import ConfigurationSoup, ControllerConfig
from nec.common.service import ReactorService
import os.path
import subprocess
import sys
import time


class ControllerService(ReactorService):

    REMOTE_INSTALL_DIR = '/tmp/divy'

    def __init__(self,
                  configurationPath,
                  **kwargs):

        super(ControllerService, self).__init__(**kwargs)

        self.configurationPath = configurationPath
        self.configuration = None

        self.installedHosts = set()
        self.backgroundProcesses = []

    def prepare(self):
        pass

    def run(self):
        print 'Parsing configuration file at "%s"' % self.configurationPath
        self._parseConfigurationFile()

        print 'Starting configured media routers'
        self._startMediaRouters(self.configuration.routers)

    def destroy(self):
        print 'Destroying ControllerService.'

        for process in self.backgroundProcesses:
            if process.poll() == None:
                print 'Terminating sub-process %s.' % process
                process.terminate()

    def _parseConfigurationFile(self):
        '''Parse the configuration objects from the provided configuration file.'''

        with open(self.configurationPath) as f:
            soup = ConfigurationSoup(f)
            self.configuration = ControllerConfig.fromSoup(soup.controller)

    def _startMediaRouters(self, routers):
        '''Starts a list of MediaRouters.'''

        for mediarouter in routers:
            # start the router we're looking at
            self._startMediaRouter(mediarouter)

            # start all downstream routers from the router we're looking at
            self._startMediaRouters(mediarouter.downstreamRouters)

    def _startMediaRouter(self, mediarouter):
        '''Start the MediaRouter process at the specified location.'''

        remoteCommandArgs = [
            'python',
            os.path.join(self.REMOTE_INSTALL_DIR, 'src', 'nec', mediarouter.SCRIPT_NAME),
            mediarouter.listeningAddress,
        ]

        if mediarouter.upstreamRoutingAddress:
            remoteCommandArgs.append(mediarouter.upstreamRoutingAddress)

        hostAddress = mediarouter.listeningAddress.split(':')[0]

        self._executeRemoteCommand(hostAddress,
                                   remoteCommandArgs)

        for generator in mediarouter.downstreamGenerators:
            self._startGenerator(generator)

    def _startGenerator(self, generator):
        '''Start the Generator process at the specified location.'''

        remoteCommandArgs = [
            'python',
            os.path.join(self.REMOTE_INSTALL_DIR, 'src', 'nec', generator.SCRIPT_NAME),
            generator.address,
            generator.routerAddress,
        ]

        hostAddress = generator.address.split(':')[0]
        self._executeRemoteCommand(hostAddress, remoteCommandArgs)

    def _executeRemoteCommand(self, address, remoteCommandArgs):
        '''Starts a remote service via 
        
        NOTE: this assumes that the local and remote machines are setup such that we don't 
        need to provide any authentication credentials here.
        
        Most likely this means that a public/private key pair must already be setup for the
        local user to authenticate with the remote host.
        '''

        self._installRemoteSources(address)

        args = [
            # The ssh executable
            'ssh',

            # disable host key checking --
            #    this makes us vulnerable to MITM-style attacks, but
            #    also allows to not fail to connect to hosts we've never seen before
            '-o', 'StrictHostKeyChecking=no',

            # where do we connect
            address,

            # ensure we're in the proper working directory
            'cd', self.REMOTE_INSTALL_DIR, '&&',

            # ensure the environment is properly setup for python on the far end
            'source', os.path.join(self.REMOTE_INSTALL_DIR, 'set_pythonpath.src'), '&&',
        ]

        # add the command arguments to be run remotely
        args.extend(remoteCommandArgs)

        # run the ssh command -- this process will run in the background
        print 'running command: %s' % ' '.join(i for i in args)
        self.backgroundProcesses.append(subprocess.Popen(args))

    def _installRemoteSources(self, address):
        '''Installs the entire source directory to a temporary location on the remote host.
        
        This ensures that when the controller starts up media routers and generators, 
        they are all using the same versions of the code. This also prevents administrators
        from needing to manage the installed versions of code on all machines -- instead, 
        they need only to ensure that the controller is run using the latest code.
        
        NOTE: this assumes that the local and remote machines are setup such that we don't 
        need to provide any authentication credentials here.
        
        Most likely this means that a public/private key pair must already be setup for the
        local user to authenticate with the remote host.
        '''
        # It's possible that multiple services are running on the same host, so
        # don't attempt to re-install to the same host multiple times.
        if address in self.installedHosts:
            return

        # use the project directory as the source
        source = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              os.path.pardir,
                                              os.path.pardir))
        destination = '%s:%s' % (address, self.REMOTE_INSTALL_DIR)

        print 'Removing existing sources from %s' % destination
        args = [
            'ssh',
            address,

            'rm', '-r', '-f', self.REMOTE_INSTALL_DIR,
        ]

        # run the ssh command to remove the remote files
        subprocess.check_call(args)

        print 'Installing sources from %s to %s' % (source, destination)
        args = [
            # the scp executable
            'scp',

            # disable host key checking --
            #    this makes us vulnerable to MITM-style attacks, but
            #    also allows to not fail to connect to hosts we've never seen before
            '-o', 'StrictHostKeyChecking=no',

            # transfer recursively
            '-r',

            # Be quiet!
            '-q',

            # source directory
            source,

            # destination
            destination,
        ]

        # run the scp command -- if anything goes wrong, this will fail
        subprocess.check_call(args)

        # add this host to the set of hosts we've installed to
        self.installedHosts.add(address)

def parseArgs(args):
    usage = '%s CONFIGURATION_FILE_PATH' % sys.argv[0]
    assert len(args) == 2, usage

    (_scriptName,
     configurationPath) = args

    assert os.path.exists(configurationPath), '%s does not exist.' % configurationPath

    return {
        'configurationPath' : configurationPath,
    }


def main():
    args = parseArgs(sys.argv)

    service = ControllerService(args['configurationPath'])
    service.start()

if __name__ == '__main__':
    main()
