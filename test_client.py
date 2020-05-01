import fakeredis
from deathnut.client.deathnut_client import DeathnutClient

fake_redis_conn = fakeredis.FakeStrictRedis()
dn_client = DeathnutClient(service="test", resource_type="recipes", redis_connection=fake_redis_conn)

# assign privileges
for privilege in ['own', 'view']:
    for i in range(3):
        dn_client.assign_role('michael', privilege, str(i))

# check privilege
assert dn_client.check_role('michael', 'view', '1') == True

# revoke privilege
dn_client.revoke_role('michael', 'view', '1')
assert dn_client.check_role('michael', 'view', '1') == False

# return all 3
assert sorted(dn_client.get_resources('michael', 'own')) == ['0', '1', '2']

# return only 2
assert len(dn_client.get_resources('michael', 'own', limit=2)) == 2

# assign some more 
for i in range(10):
    dn_client.assign_role('michael', 'own', str(i + 3))

# three pages of results [5, 5, 3]
assert len(list(dn_client.get_resources_page('michael', 'own', page_size=5))) == 3

# page through results
for i, page in enumerate(dn_client.get_resources_page('michael', 'own', page_size=5)):
    assert len(page) == [5, 5, 3][i]

# show all roles and ids
all_roles = dn_client.get_roles('michael')
assert sorted(all_roles['own']) == ['0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9']
assert sorted(all_roles['view']) == ['0', '2']
