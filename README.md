change range to xrange in python < 3

range(var-1, -1, -1)    ===>    reverse


use enumerate, izip, sorted (compare via key)

for block in iter(partial(f.read, 32), ''):
	blocks.append(block)