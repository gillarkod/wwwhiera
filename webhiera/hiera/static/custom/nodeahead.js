$(document).ready(function () {
    var n_search = $("#node_search");

    var m_show = $("#module_show");
    var m_hide = $("#module_hide");

    var f_show = $("#file_show");
    var f_hide = $("#file_hide");

    var a = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace("certname"),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {url: "/hiera/nodes/%QUERY", wildcard: "%QUERY"}
    });

    $(n_search).typeahead({highlight: !0}, {
        name: "node_search",
        display: "certname",
        source: a
    });

    $(n_search).bind("typeahead:select", function (t, e) {
        $(n_search).attr("certname", e.certname);
        get_hiera_data();
    });
    $(m_show).change(function () {
        var certname = $(n_search).attr('certname');
        if (certname) {
            get_hiera_data()
        }
    });
    $(m_hide).change(function () {
        var certname = $(n_search).attr('certname');
        if (certname) {
            get_hiera_data()
        }
    });
    $(f_show).change(function () {
        var certname = $(n_search).attr('certname');
        if (certname) {
            get_hiera_data()
        }
    });
    $(f_hide).change(function () {
        var certname = $(n_search).attr('certname');
        if (certname) {
            get_hiera_data()
        }
    });
});

function get_hiera_data() {
    var certname = $("#node_search").attr('certname');

    var url = '/hiera/node/' + certname;
    var search_params = '?';

    var m_show = $("#module_show").val();
    if (m_show) {
        search_params += 'module_show=' + m_show + '&'
    }

    var m_hide = $("#module_hide").val();
    if (m_hide) {
        search_params += 'module_hide=' + m_hide + '&'
    }

    var f_show = $("#file_show").val();
    if (f_show) {
        search_params += 'file_show=' + f_show + '&'
    }

    var f_hide = $("#file_hide").val();
    if (f_hide) {
        search_params += 'file_hide=' + f_hide + '&'
    }

    url = url + search_params;

    $.get(url, function (json) {
        var response = $(jQuery(json));
        var hiera = response[0]['data'];
        $("#hiera_data").html(hiera);
    });


}



