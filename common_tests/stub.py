#
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class Stub(object):
    """
    Simple stub class. This can be inserted in place of a function, i.e.

        instance.somefunc = Stub

    Then, when instance.somefunc(*args, **kwargs) is called, we can record this.
    This is similar to python Mock functionality, however this works more nicely
    for comparing return values of a function, i.e. if some other function
    returns instance.somefunc().
    """

    def __init__(self, stub_for, *args, **kwargs):
        self.stub_for = stub_for
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def __eq__(self, other):
        return (self.stub_for == other.stub_for
                and self.args == other.args
                and self.kwargs == other.kwargs)

    def __repr__(self):
        return '{0} {1}'.format(self.__class__, self.__str__())

    def __str__(self):
        return 'Stub:{0} args: {1}, kwargs: {2}'.format(self.stub_for,
                                                        self.args,
                                                        self.kwargs)


class HttpStub(Stub):

    def __call__(self, *args, **kwargs):
        return self

    def request(self, *args, **kwargs):
        return self.args


class KeyStub(Stub):

    def __init__(self, kind, name, *args, **kwargs):
        super(KeyStub, self).__init__('datastore.key.Key', *args, **kwargs)
        self.kind = kind
        self.name = name

        # Could be improved in the future to mimic the actual datastore.key.Key
        # behavior 
        self.path = ''

    def __eq__(self, other):
        eq = True
        eq &= self.kind == other.kind
        eq &= self.name == other.name
        return eq and super(KeyStub, self).__eq__(other)

    def __str__(self):
        template = 'KeyStub: <kind: {0}> <name: {1}> <args: {2}> <kwargs: {3}'
        return template.format(self.kind, self.name, self.args, self.kwargs)


class QueryStub(Stub):

    def __init__(self, stub_for, ret_list, *args, **kwargs):
        super(QueryStub, self).__init__(stub_for, *args, **kwargs)
        self.filters = list()
        self.ret_list = ret_list

    def add_filter(self, field, cmp, value):
        self.filters.append((field, cmp, value))

    def fetch(self):
        return self.ret_list
