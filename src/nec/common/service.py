'''
Created on Dec 30, 2009

@author: chris
'''
from twisted.internet import reactor
from twisted.python import log
from twisted.python.logfile import LogFile
import os.path


class ReactorService(object):
    '''Provides a Twisted reactor-driven service.'''

    def __init__(self,
                  logStream = None,
                  loggingEnabled = True,
                  **kwargs):
        self.reactor = reactor

        self.logStream = logStream
        self.loggingEnabled = loggingEnabled

    @property
    def shortIdentifier(self):
        '''Provide a simple short name for use in log file names.
        
        Subclasses should override this property to provide a name that
        uniquely identifies instances of the class if possible.
        '''
        return self.__class__.__name__

    def start(self):
        self._setupLogging()

        # Run our setup code before attempting to start the reactor
        self.prepare()

        try:
            # Schedule the service to run
            reactor.callLater(0, self.run)

            # Start the reactor
            reactor.run()

        finally:
            # Ensure that our cleanup code has a chance to run after the reactor has stopped
            self.destroy()


    def prepare(self):
        '''Do any work required before the reactor is started.
        
        Subclasses should override this method with any code required 
        to be run before the reactor has been started.
        '''
        pass

    def run(self):
        '''Do the main work for the service.
        
        Subclasses should override this method with any code required 
        to be run after the reactor has been started.  
        '''
        pass

    def destroy(self):
        '''Do any work required after the reactor is stopped.
        
        Subclasses should override this method with any code required 
        to be run after the reactor has been stopped.'''
        pass

    def _setupLogging(self):
        if not self.loggingEnabled:
            return

        if not self.logStream:
            logFileDirectory = '/tmp'
            logFileName = 'divy_%s.log' % self.shortIdentifier

            # HACK: Just picks a logfile and sends everything there.
            self.logStream = LogFile(name = logFileName,
                                     directory = logFileDirectory)

            print 'Note: all future output is directed to %s' % os.path.join(logFileDirectory,
                                                                             logFileName)
            print '    To view logs, run "tail -f /tmp/divy_*.log" in a shell.'

        log.startLogging(self.logStream)
