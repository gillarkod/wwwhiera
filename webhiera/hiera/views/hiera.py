"""
Lookup hiera configuration for a node
"""
import json

from django.http import HttpResponseBadRequest
from django.shortcuts import HttpResponse, render

from webhiera.hiera.methods.puppetviewer import get_hiera_data
from webhiera.hiera.pdb.fetch import get_data


def home(request):
    return render(request, 'home.html')


def hiera(request, certname):
    context = dict()

    module_show = request.GET.get('module_show', None)
    module_hide = request.GET.get('module_hide', None)

    file_show = request.GET.get('file_show', None)
    file_hide = request.GET.get('file_hide', None)

    if module_show:
        module_show = module_show.split(' ')
    if module_hide:
        module_hide = module_hide.split(' ')
    if file_show:
        file_show = file_show.split(' ')
    if file_hide:
        file_hide = file_hide.split(' ')
    context['data'] = get_hiera_data(
        node=certname,
        show_modules=module_show,
        hide_modules=module_hide,
        show_files=file_show,
        hide_files=file_hide,
    )

    return HttpResponse(json.dumps(context, indent=2), content_type="application/json")


def get_nodes(request, search_q=None):
    """
    Used to search for nodes matching a regex
    :param request: The user request
    :param search_q: search query
    :return: Search result
    :rtype: Dict
    """

    context = dict()

    if not search_q:
        context['error'] = 'Must specify something to search for.'
        return HttpResponseBadRequest(context)

    search_nodes = {
        'query': '["~","certname","%s"]' % search_q,
        'order-by': '[{"field": "certname", "order": "desc"}]',
        'limit': '10'
    }

    search_result = get_data('nodes', query=search_nodes)
    return HttpResponse(json.dumps(search_result, indent=2), content_type="application/json")
