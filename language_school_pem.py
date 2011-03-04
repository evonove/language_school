# -*- coding: utf-8 -*-
#
# Copyright 2010 Evonove srl <info@evonove.it>
#
# This file is part of language_school OpenERP addon.
#
# language_school is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# language_school is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#
"""Poweremail customization module. 

Extends poweremail model data and behaviour
"""
from osv import osv, fields
from tools.translate import _
import tools, netsvc
import time

# Monkeypatch send wizard: at the moment (OpenERP v5.0.12) it's not possible
# to inherit from osv.osv_memory
from poweremail.poweremail_send_wizard import poweremail_send_wizard
def save_to_mailbox(self, cr, uid, ids, context=None):
    def get_end_value(id, value):
        if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets value from the template
            return self.get_value(cr, uid, template, value, context, id)
        else:
            return value

    logger = netsvc.Logger()
    mail_ids = []
    template = self._get_template(cr, uid, context)
    for id in context['src_rec_ids']:
        # if we're sending a newsletter, skip objects flagged with 'block_newsletter'
        model_name = template.model_int_name
        # models for which performing newsletter check
        dest_models = ['language.school.alia.student']
        if template.is_newsletter and model_name in dest_models:
            object = self.pool.get(model_name).browse(cursor, user, id, context)
            try:
                if object.block_newsletter:
                    continue
            except AttributeError:
                logger.notifyChannel(_("Language School"), netsvc.LOG_ERROR, 
                    _("Recipient object has no attribute 'block_newsletter', skip..."))
                continue
        
        screen_vals = self.read(cr, uid, ids[0], [],context)[0]
        accounts = self.pool.get('poweremail.core_accounts').read(cr, uid, screen_vals['from'], context=context)
        mail_type = "text/plain"
        if screen_vals['body_html']:
            mail_type = "text/html"
        vals = {
            'pem_from': tools.ustr(accounts['name']) + "<" + tools.ustr(accounts['email_id']) + ">",
            'pem_to': get_end_value(id, screen_vals['to']),
            'pem_cc': get_end_value(id, screen_vals['cc']),
            'pem_bcc': get_end_value(id, screen_vals['bcc']),
            'pem_subject': get_end_value(id, screen_vals['subject']),
            'pem_body_text': get_end_value(id, screen_vals['body_text']),
            'pem_body_html': get_end_value(id, screen_vals['body_html']),
            'pem_account_id': screen_vals['from'],
            'state':'na',
            'mail_type': mail_type,
        }
        if screen_vals['signature']:
            signature = self.pool.get('res.users').read(cr, uid, uid, ['signature'], context)['signature']
            if signature:
                vals['pem_body_text'] = tools.ustr(vals['pem_body_text'] or '') + signature
                vals['pem_body_html'] = tools.ustr(vals['pem_body_html'] or '') + signature

        attachment_ids = []

        #Create partly the mail and later update attachments
        mail_id = self.pool.get('poweremail.mailbox').create(cr, uid, vals, context)
        mail_ids.append(mail_id)
        if template.report_template:
            reportname = 'report.' + self.pool.get('ir.actions.report.xml').read(cr, uid, template.report_template.id, ['report_name'], context)['report_name']
            data = {}
            data['model'] = self.pool.get('ir.model').browse(cr, uid, screen_vals['rel_model'], context).model

            # Ensure report is rendered using template's language
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = self.get_value(cr, uid, template, template.lang, context, id)
            service = netsvc.LocalService(reportname)
            (result, format) = service.create(cr, uid, [id], data, ctx)
            attachment_id = self.pool.get('ir.attachment').create(cr, uid, {
                'name': _('%s (Email Attachment)') % tools.ustr(vals['pem_subject']),
                'datas': base64.b64encode(result),
                'datas_fname': tools.ustr(get_end_value(id, screen_vals['report']) or _('Report')) + "." + format,
                'description': vals['pem_body_text'] or _("No Description"),
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id
            }, context)
            attachment_ids.append( attachment_id )

        # Add document attachments
        for attachment_id in screen_vals.get('attachment_ids',[]):
            new_id = self.pool.get('ir.attachment').copy(cr, uid, attachment_id, {
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id,
            }, context)
            attachment_ids.append( new_id )

        # Add template attachments
        if template.attachments:
            attachment_ids.append(template.attachments)
            #attachment_ids = [x.id for x in template.attachments]
            #self.pool.get('poweremail.mailbox').write(cr,uid,mail_id,{'pem_attachments_ids':[(6,0,attachment_ids)],'mail_type':'multipart/mixed'})

        # TODO BAD BAD BAD. Any better idea is welcome!
        course = self.pool.get(template.model_int_name).browse(cr, uid, id, context)
        if template.name == 'Conferma Alloggio':
            # attach pics if present
            for stay in course.stay_ids:
                if stay.lodge_id.pics:
                    for p in stay.lodge_id.pics:
                        attachment_ids.append(p.id)
            # store current time
            self.pool.get('language.school.course').write(cr,uid,course.id,{
                'lodge_confirm_sent_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
        elif template.name == 'Invia Proforma':
            # store current time
            self.pool.get('language.school.course').write(cr,uid,course.id,{
                'proforma_sent_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            })

        if attachment_ids:
            self.pool.get('poweremail.mailbox').write(cr, uid, mail_id, {
                'pem_attachments_ids': [[6, 0, attachment_ids]],
                'mail_type': 'multipart/mixed'
            }, context)
        
        # Create a partner event
        if template.partner_event and template.partner_event_type_id and self.pool.get('res.partner.event.type').check(cr, uid, template.partner_event_type_id.key) and self._get_template_value(cr, uid, 'partner_event', context):
            name = vals['pem_subject']
            if isinstance(name, str):
                name = unicode(name, 'utf-8')
            if len(name) > 64:
                name = name[:61] + '...'
            document = False
            if template.report_template and self.pool.get('res.request.link').search(cr, uid, [('object','=',data['model'])], context=context):
                document = data['model']+',%i' % id
            elif attachment_ids and self.pool.get('res.request.link').search(cr, uid, [('object','=','ir.attachment')], context=context):
                document = 'ir.attachment,%i' % attachment_ids[0]
            self.pool.get('res.partner.event').create(cr, uid, {
                'name': name,
                'description': vals['pem_body_text'] and vals['pem_body_text'] or vals['pem_body_html'],
                'partner_id': self.get_value(cr, uid, template, template.partner_event, context, id),
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'canal_id': template.canal_id and template.canal_id.id or False,
                'partner_type': template.partner_type,
                'user_id': uid,
                'document': document,
            })

    return mail_ids
poweremail_send_wizard.save_to_mailbox = save_to_mailbox

class language_school_poweremail_template(osv.osv):
    """Extends poweremail template to support attachments and newsletters
    
    poweremail doesn't support defining attachments for a template. Currently
    user can only attach a file during send wizard; so if a template with the
    same attach has to be sent regularly, it has to be re-attached every time.
    
    is_newsletter it's a simple flag who tells the wizard to check if
    object associated to the template has the flag 'block_newsletter': in case
    it avoids to send mail to that recipient. It's a trivial way to support 
    optin/optout operations.
    """
    _name = "poweremail.templates"
    _inherit = "poweremail.templates"
    
    _columns = {
        'attachments':fields.many2many('ir.attachment', 'language_school_mail_attachments_rel', 'mail_id', 'att_id', 'Allegati'),
        'is_newsletter' : fields.boolean('Template per newsletter'),
    }
    
    _defaults = {
        'is_newsletter' : lambda *a: False,
    }
language_school_poweremail_template()
