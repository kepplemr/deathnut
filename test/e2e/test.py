
def testing():
  a = 3
  print 'hello'

testing()
testing.test = 'abc'
print(str(testing.__dict__))
#print(dir(testing))


for attr in dir(testing):
  print('{} : {}'.format(attr, getattr(testing, attr)))
testing.__try__ = testing.__dict__.get('testing', {})
