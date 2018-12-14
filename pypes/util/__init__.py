from cStringIO import StringIO
import sys
from contextlib import contextmanager
from pypes.util.errors import PypesException

@contextmanager
def ignored(*exceptions):
	try:
		yield
	except exceptions:
		pass

@contextmanager
def exception_override(target_exception=PypesException, *exceptions):
	try:
		yield
	except exceptions:
		raise target_exception()

def redirect_stdout(fileobj):
	oldstdout = sys.stdout
	sys.stdout = fileobj
	try:
		yield fileobj
	finally:
		sys.stdout = oldstdout

class InvalidOperationException(Exception):
	pass

def fixed_returns(actual_return=None, num_returns=2):
	if num_returns < 1:
		raise InvalidOperationException()
	new_tuple = tuple()
	if isinstance(actual_return, tuple):
		new_tuple += tuple([cur_return for cur_return in actual_return[:num_returns]])
		new_tuple += tuple([None for cur_return in xrange(num_returns-len(actual_return))])
	else:
		new_tuple += (actual_return,)
		new_tuple += tuple([None for cur_return in xrange(num_returns-1)])
	return new_tuple

remove_dupes = lambda initial: reduce(lambda new_list, item: (new_list + ([item] if not item in new_list else [])), [[]] + initial)

def __raise_exception(exception):
	raise exception()

raise_exception_func = lambda exception: lambda *args, **kwargs: __raise_exception(exception)

class StringWrapper:
	def __init__(self):
		self.str = ""
	def write(self, str):
		self.str += str
	def __str__(self):
		return self.str
	def __len__(self):
		return len(self.str)

class RedirectStdStreams(object):
	
	def __init__(self):
		self.stdout = StringWrapper()
		self.stderr = StringWrapper()

	def __enter__(self):
		self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
		self.old_stdout.flush(); self.old_stderr.flush()
		sys.stdout, sys.stderr = self.stdout, self.stderr

	def __exit__(self, exc_type, exc_value, traceback):
		sys.stdout = self.old_stdout
		sys.stderr = self.old_stderr
