'''
Created on Dec 30, 2009

@author: chris
'''

from BeautifulSoup import BeautifulStoneSoup, Tag


class ConfigurationSoup(BeautifulStoneSoup):
    '''Provides special-case parsing for BeautifulSoup.
    
    The BeautifulSoup classes are designed to automatically clean up BAD
    markup, and so make some assumptions during parsing that may not be great
    for syntactially valid markup.
    
    In this case, it is acceptable for 'routers' tags to be nested such that
    they form a hierarchy, if that nesting is contained within a 'controller' 
    or 'mediarouter' tag.
    
    For more info, see:
        http://www.crummy.com/software/BeautifulSoup/documentation.html#Customizing%20the%20Parser
    '''

    NESTABLE_TAGS = {
        'routers' : ['controller', 'mediarouter'],
        'mediarouter' : ['routers', ],
    }

# The default for the "recursive" parameter in the Tag.find and Tag.findAll
# methods makes for some confusing behavior. Let's reach in and dynamically
# "fix" this problem by making the default be non-recursive
Tag.find.im_func.__defaults__ = (None, # name - same
                                 {}, # attrs - same
                                 False, # recursive - changed from True
                                 None)  # text - same

Tag.findAll.im_func.__defaults__ = (None, # name - same
                                    {}, # attrs - same
                                    False, # recursive - changed from True
                                    None, # text - same
                                    None) # limit - same


class SoupConfigBase(object):

    def __init__(self):
        if cls is SoupConfigBase:
            raise NotImplementedError('%s is abstract and should not be directly instantiated.')

    @classmethod
    def assertSoupName(cls, soup):
        '''Check that the name of the soup matches the expected name.
        
        This should be called as the first line of any fromSoup() implementation.
        '''
        if soup.name != cls.SOUP_NAME:
            raise Exception('Unexpected name for %s: %s' % (cls.__name__,
                                                            soup.name))

    @classmethod
    def fromSoup(cls, soup):
        raise NotImplementedError('%s does not implement the abstract classmethod fromSoup()' % cls.__name__)


class GeneratorConfig(SoupConfigBase):

    SOUP_NAME = 'generator'
    SCRIPT_NAME = 'generator.py'

    def __init__(self, address, routerAddress):
        self.address = address
        self.routerAddress = routerAddress

    @classmethod
    def fromSoup(cls, soup):
        cls.assertSoupName(soup)

        address = soup.address.string

        routerAddress = None
        if soup.parent.parent.name == MediaRouterConfig.SOUP_NAME:
            routerAddress = soup.parent.parent.address.string
        assert routerAddress, 'Generator must have a parent router address.'

        return GeneratorConfig(address, routerAddress)


class MediaRouterConfig(SoupConfigBase):

    SOUP_NAME = 'mediarouter'
    SCRIPT_NAME = 'mediarouter.py'

    def __init__(self,
                  listeningAddress,
                  upstreamRoutingAddress,
                  downstreamRouters,
                  downstreamGenerators):

        self.listeningAddress = listeningAddress
        self.upstreamRoutingAddress = upstreamRoutingAddress
        self.downstreamRouters = downstreamRouters or []
        self.downstreamGenerators = downstreamGenerators or []

    @classmethod
    def fromSoup(cls, soup):
        cls.assertSoupName(soup)

        listeningAddress = soup.address.string

        upstreamRoutingAddress = None
        if soup.parent.parent.name == MediaRouterConfig.SOUP_NAME:
            upstreamRoutingAddress = soup.parent.parent.address.string

        downstreamRouters = []
        if soup.routers:
            downstreamRouters = [MediaRouterConfig.fromSoup(routerSoup)
                                 for routerSoup in soup.routers.findAll(cls.SOUP_NAME)]


        downstreamGenerators = []
        if soup.generators:
            downstreamGenerators = [GeneratorConfig.fromSoup(generatorSoup)
                                    for generatorSoup in soup.generators.findAll(GeneratorConfig.SOUP_NAME)]

        return MediaRouterConfig(listeningAddress,
                                 upstreamRoutingAddress,
                                 downstreamRouters,
                                 downstreamGenerators)


class ControllerConfig(SoupConfigBase):

    SOUP_NAME = 'controller'

    def __init__(self, address, routers):
        self.address = address
        self.routers = routers

    @classmethod
    def fromSoup(cls, soup):
        cls.assertSoupName(soup)

        print 'controller config: '
        print soup.prettify()

        address = soup.address.string
        routers = [MediaRouterConfig.fromSoup(routerSoup)
                   for routerSoup in soup.routers.findAll('mediarouter')]

        return ControllerConfig(address, routers)
