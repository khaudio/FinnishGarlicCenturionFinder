from chimestock import chimestock

try:
    from private import privateKwargs
    from private import urls
except:
    privateKwargs = dict()
    urls = []

if __name__ == '__main__':
    with chimestock.Clerk(*urls, **privateKwargs) as clerk:
        pass
