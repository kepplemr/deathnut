from google.cloud import datastore
import yaml

datastore_client = datastore.Client(project='wellio-integration')

query = datastore_client.query(kind='recipe')
query.add_filter('title', '=', 'perftest6')
query.keys_only()
resp = query.fetch()

entities = list(resp)
print('Size of respone: ' + str(len(entities)))
