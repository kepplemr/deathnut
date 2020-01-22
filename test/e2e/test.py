
def testing():
  a = 3
  print 'hello'

testing()
testing.test = 'abc'
print(str(testing.__dict__))
#print(dir(testing))
testing.__try__ = testing.__dict__.get('testing', {})
