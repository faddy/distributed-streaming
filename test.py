
class Task:
    def __init__(self, service):
	self.t_a = 4
	self.t_b = 9
	self.service = service

    def print_task(self):
	print self.t_a, self.t_b
	hello = 'hello from task'
	self.service.print_hello(hello)


class MediaRouterService:
    def __init__(self):
        self.a= 5
        self.b =10

    def print_media(self):
	print self.a, self.b
	t = Task(self)
	t.print_task()

    def print_hello(self, hello):
	print hello

def test_func(x):
    dic = {1:'a', 2:'b', 3:'b'}
    if (x==1):
	return dic

def main():
    #service = MediaRouterService()
    #service.print_media()
    x = input
    print x

if __name__ == '__main__':
    main()
