#!/usr/local/bin/python

import sys
import os
import cgitb
from web.reportutils import HTML, markup
from plant.resources import res

def run(func, *args, **kwargs):
    conf = res.conf
    
    if conf.get("cgi", {}).get("errors_on_screen", False):
        cgitb.enable()
        return func(*args, **kwargs)
    
    try:
        return func(*args, **kwargs)        
    except Exception, e:
        
        # Send traceback in an email to conf.cgi.error_waters
        import emailer
        system_name = conf.get("system", {}).get("name", "Undefined")
        if 'REMOTE_USER' in os.environ:
            system_name = '%s: %s' % (system_name, os.environ['REMOTE_USER'])
        email = conf.get("cgi", {}).get("error_watchers",
                                        ["greenteam@mypublisher.com"])
        filename = os.path.basename(sys.argv[0])
        emailer.emailer(emailTo=email,
                        emailFrom='plant@mypublisher.com',
                        emailSubject='PLANT_ERROR: %s: %s: %s' % \
                           (system_name, filename, str(e)[:40]),
                        emailHtml=cgitb.html(sys.exc_info()),
                        emailText=cgitb.text(sys.exc_info()))

        # display message to user.
        logo = "<img src='images/mypub_logo.jpg'/>"
        button = '<a href="javascript:back()">GO BACK</a>'
        msg = markup('''
        An Unexpected Error Occurred: !%s!
        Details have been sent to %s

        ''' % (e, email))
        error_page = """
        <table style='border: 0' width='100%%' border='0'>
          <tr>
             <td style='border: 0;' width='30px' valign='top'>%s</td>
             <td style='border: 0;'>%s</td>
          </tr>
        </table>""" % (logo, msg) + button
        return HTML(msg=error_page)
