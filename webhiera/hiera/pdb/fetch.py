import json
import urllib.parse as urlparse

import requests
from constance import config


def get_data(endpoint, query=None):
    headers = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
    }
    api_url = config.PUPPETDB_HOST

    if api_url[-1] != '/':
        api_url = '{0}/'.format(api_url)

    if endpoint[0] == '/':
        endpoint = endpoint.lstrip('/')

    if endpoint.split('/')[0]:
        endpoint = 'v4/%s' % endpoint

    if query:
        endpoint += '?{0}'.format(urlparse.urlencode(query))

    url = '{0}{1}'.format(api_url, endpoint)

    if config.PUPPETDB_VERIFY_SSL:
        ssl_verify = config.PUPPETDB_CA_CERT
        ssl_certs = (config.PUPPETDB_PUB_KEY, config.PUPPETDB_PRIV_KEY)
    else:
        ssl_verify = False
        ssl_certs = None

    resp = requests.get(
        url=url,
        params={},
        headers=headers,
        verify=ssl_verify,
        cert=ssl_certs,
    )

    try:
        return json.loads(resp.text)
    except:
        return []
