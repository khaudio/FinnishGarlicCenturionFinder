#!/usr/bin/env python

"""
Checks stock on specified items, and sends email notifications
when changes are detected.  Applicably, it helps the user
obtain rare items during shortages.
"""

import aiohttp
import async_timeout
import getpass
import re
import smtplib
import asyncio


class Item:
    """
    Class for containing state of individual items; methods update state
    by awaiting update().

    Item does not need to be directly instantiated; Store will create one
    per provided url.
    """
    def __init__(self, url):
        self.url = url
        self.stock = None
        self.stockChanged = False
        self.loop = asyncio.get_event_loop()
        self.stockString = 'In stock'

    def __str__(self):
        stock = 'in' if self.stock else 'out of'
        return f'Item is {stock} stock\n{self.url}\n'

    async def pull(self):
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(self.url) as response:
                    return await response.text()

    async def update(self):
        text = await self.pull()
        if not text:
            raise ValueError('Data missing from request')
        stock = bool(re.search(self.stockString, text))
        self.stockChanged = (stock != self.stock and self.stock is not None)
        self.stock = stock


class Store:
    """
    Periodically checks a given list of urls for stock changes

    Required is valid email account information for notifications.
    If a recipient address is not provided, the user will be prompted for one.
    If the prompt is empty, notifications are sent from the sender
    address to itself.  Providing an empty string for recipient is a valid
    argument to enable loopback operation, as only a value of None
    will trigger a prompt.

    The default time between checks is 15 minutes.  This value should
    be at least a few minutes, to avoid being blacklisted by the
    server, though this class enforces no such limit.  To change the
    time period, provide a value in minutes to self.run(minutes).

    Setting debug to True enables false positives for testing
    """

    def __init__(
            self, server=None, port=587, sender=None,
            password=None, recipient=None, debug=False
        ):
        self.items, self.newInStock, self.totalInStock = set(), 0, 0
        self.debug = debug
        self.server = 'smtp.gmail.com' if server is None else server
        self.port = port
        if not sender:
            self.sender = input('Enter sender email address: ').lstrip().rstrip()
        else:
            self.sender = sender
        if recipient is None:
            prompted = input('Enter recipient email address (Leave blank for loopback): ').lstrip().rstrip()
            if not prompted:
                self.recipient = self.sender
            else:
                self.recipient = prompted
        else:
            self.recipient = self.sender
        if self.server and self.sender and not password:
            self.__password = getpass.getpass('Enter email account password: ')
        else:
            self.__password = password
        self.loop = asyncio.get_event_loop()

    def __str__(self):
        return '\n'.join(item.__str__() for item in self.items)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.loop.close()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, val):
        assert isinstance(val, int), 'Must be int'
        self._port = val

    @property
    def sender(self):
        return self._sender

    @sender.setter
    def sender(self, val):
        assert val is not None, 'Sender address cannot be empty'
        assert isinstance(val, str), 'Must be str'
        self._sender = val

    def run(self, minutes=15):
        run = asyncio.ensure_future(self.check(minutes))
        self.loop.run_forever()

    async def check(self, minutes=15):
        assert isinstance(minutes, (int, float)), 'Minutes must be an integer or float'
        seconds = minutes * 60
        while True:
            print('Checking stock...')
            await self.update()
            if self.newInStock:
                print('New items available')
                if self.send_email():
                    print('Recipient notified of stock changes')
            else:
                print('Stock unchanged')
            await asyncio.sleep(seconds)

    def add(self, *urls):
        for url in urls:
            assert isinstance(url, str), 'URL must be a string'
            if url not in (item.url for item in self.items):
                new = Item(url)
                self.loop.run_until_complete(new.update())
                self.items.add(new)

    def remove(self, *urls):
        for url in urls:
            assert isinstance(url, str), 'URL must be a string'
        self.items = set(filter(lambda item: item.url not in urls, self.items))

    def email_message(self):
        if self.debug:
            new = self.items
        else:
            new = tuple(filter(lambda item: item.stockChanged, self.items))
        message = '\n'.join(item.__str__() for item in new)
        print(message)
        return message

    def email_subject(self):
        return f'({self.newInStock} new, {self.totalInStock} total) items in stock'

    def send_email(self):
        server = smtplib.SMTP(self.server, self.port)
        server.ehlo()
        server.starttls()
        server.login(self.sender, self.__password)
        body = '\n'.join([
                f'To: {self.recipient}',
                f'From: {self.sender}',
                f'Subject: {self.email_subject()}\n',
                self.email_message()
            ])
        try:
            server.sendmail(self.sender, self.recipient, body)
        except:
            sent = False
        else:
            sent = True
        finally:
            server.quit()
        return sent

    async def update(self):
        for item in self.items:
            await item.update()
        if self.debug:
            self.newInStock = self.totalInStock = len(self.items)
        else:
            self.newInStock = sum(item.stockChanged for item in self.items)
            self.totalInStock = sum(item.stock for item in self.items)


class Clerk(Store):
    """
    Further abstraction and automation of Store

    Instantiate Clerk with a list of urls as arguments.
    Clerk exists to be able to start and run a Store in one line.
    The user will be prompted for email account information.
    """

    def __init__(self, *urls, minutes=15, **kwargs):
        super().__init__(**kwargs)
        super().add(*urls)
        super().run(minutes=minutes)
