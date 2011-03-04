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
"""Main module. 

Defines models for the most of the objects handled by language_school addon.
"""
from osv import osv, fields
from tools.misc import debug
from tools import config
from tools.translate import _
import time
import datetime


class Country(osv.osv):
    """This is a workaround
    
    In the view, countries are ordered by code, not by name. This causes a 
    weird sorting when countries are displayed in local translation.
    e.g. "Isole Cayman" is shown under "C" letter ("Cayman Islands") instead 
    of "I"
    Inheriting Country invalidate translations, so countries are displayed 
    always in english (and correctly ordered indeed)
    
    """
    _name = 'res.country'
    _description = 'Country'
    _inherit = 'res.country'
            
    def name_get(self, cr, user, ids, context={}):
        ''
        res = []
        for rec in self.read(cr, user, ids, ['name','code']):
            #name = '%s - %s' % (rec['code'], rec['name'])
            name = rec['name']
            res.append( (rec['id'],name) )
        return res
    
    _columns = {
        'student_id' : fields.one2many('language.school.alia.student', 'country_id'),
    }
Country()


class res_partner(osv.osv):
    """Extends partners to support lodges"""
    _description='ALIA Partners'
    _name = "res.partner"
    _inherit = "res.partner"
    
    def _main_contact(self, cr, uid, ids, fields, arg, context=None):
        res = dict.fromkeys(ids, 0)
        for partner in self.browse(cr, uid, ids, context):
            contact_ids = self.pool.get('res.partner.contact').search(cr, uid, [('partner_id', '=', partner.id)])
            if len(contact_ids):
                res[partner.id] = contact_ids[0]
        return res
    
    _columns = {
        'lodge' : fields.boolean('Alloggio', help="Il partner rappresenta un alloggio"),
        'link_to_map' : fields.char('Google Maps Link', size=300),
        'students' : fields.one2many('language.school.alia.student', 'contact_id'),
        'main_contact_id' : fields.function(_main_contact, type='many2one', relation='res.partner.contact', store=False, method=True, string='Contatto principale'),
        'vat' : fields.char('VAT', size=20),
        'pics':fields.many2many('ir.attachment', 'language_school_lodge_pics_rel', 'lodge_id', 'att_id', 'Foto'),
    }
res_partner()


class language_school_alia_student(osv.osv):
    """Base class needed to avoid ciclic dependencies"""
    
    _name = 'language.school.alia.student'
language_school_alia_student()


class language_school_session(osv.osv):
    """Base class needed to avoid ciclic dependencies"""
    
    _name = 'language.school.session'
language_school_session()


class language_school_course_level(osv.osv):
    """Base class needed to avoid ciclic dependencies"""
    
    _name = 'language.school.course.level'
language_school_course_level()

class language_school_course(osv.osv):
    """A course is a collection of sessions a student attended at the school.
    The course is something for what students pay and get back an invoice
    
    """
    _name = 'language.school.course'
    _description = 'Corsi'
    
    def _count_hours(self, cr, uid, ids, field_name, arg, context=None):
        'Sum hours of all the sessions for this course'
        # init hours to 0 for requested ids
        hours = dict.fromkeys(ids, 0)
        for course in self.browse(cr, uid, ids, context):
            # retrieve all the sessions and sum the hours
            for session in course.session_ids:
                hours[course.id] += session.hours
        return hours
    
    def _start_date(self, cr, uid, ids, field_name, arg, context=None):
        """Retrieve the earliest starting date among all sessions 
        for this course
        
        """
        from mx.DateTime import Parser, MaxDateTime
        
        dates = dict.fromkeys(ids, str(MaxDateTime))
        for course in self.browse(cr, uid, ids, context):
            for session in course.session_ids:
                earliest_date = Parser.DateFromString(dates[course.id])
                session_date = Parser.DateFromString(session.start_date)
                if session_date < earliest_date:
                    dates[course.id] = session.start_date
            # default value: don't display anything
            if dates[course.id] == str(MaxDateTime):
                dates[course.id] = ''
        
        return dates
    
    def _end_date(self, cr, uid, ids, field_name, arg, context=None):
        'Retrieve the latest ending date among all sessions'
        from mx.DateTime import Parser, MinDateTime
        
        dates = dict.fromkeys(ids, str(MinDateTime))
        for course in self.browse(cr, uid, ids, context):
            for session in course.session_ids:
                latest_date = Parser.DateFromString(dates[course.id])
                session_date = Parser.DateFromString(session.end_date)
                if session_date > latest_date:
                    dates[course.id] = session.end_date
            # default value: don't display anything
            if dates[course.id] == str(MinDateTime):
                dates[course.id] = ''

        return dates
    
    def onchange_session(self, cr, uid, ids, session_ids, context=None):
        'compute total of CFUs when a session is added'
        result = {}
        
        # session_ids comes in the form [(6, 0, [session ids])]
        session_ids = session_ids[0][2]
        #self.write(cr, uid, ids, {'session_ids' : session_ids})

        total = 0
        sessions = self.pool.get('language.school.session').browse(cr,uid,session_ids)
        for s in sessions:
            total += s.hours

        result['value'] = {
            'cfu': self._compute_cfu(total),
        }
        return result
    
    def _compute_cfu(self, hours):
        cfus = 0
        if 60 <= hours <= 80:
            cfus = 15
        elif 80 < hours <= 100:
            cfus = 20
        elif 100 < hours: # <=120:
            cfus = 30
        
        return cfus
    
    def _individual_hours(self, cr, uid, ids, field_name, arg, context=None):
        ''
        ind_hours = self._count_hours(cr, uid, ids, field_name, arg, context)
        for k,v in ind_hours.iteritems():
            ind_hours[k] = int(round(v / 2.0))

        return ind_hours
    
    def _total_amount(self, cr, uid, ids, field_name, arg, context=None):
        ''
        totals = dict.fromkeys(ids, 0.0)
        
        for course in self.browse(cr, uid, ids, context):
            for fee in course.fee_ids:
                totals[course.id] += fee.amount

        return totals
        
    def get_accommodations(self, cr, uid, ids, context=None):
        ''
        result = []
        course = self.browse(cr, uid, ids, context)[0]
        for s in course.stay_ids:
            # name_get returns a list of tuples (id, name)
            label = '%s (%s)' % (s.lodge_id.name, s.name_get()[0][1])
            result.append(label)
        
        return ', '.join(result)
    
    def get_vat_number(self, cr, uid, ids, context=None):
        ''
        course = self.browse(cr, uid, ids, context)[0]
        if course.student_id.contact_id:
            return course.student_id.contact_id.vat
        return ''
    
    def get_session_types(self, cr, uid, ids, context=None):
        ''
        types = []
        course = self.browse(cr, uid, ids, context)[0]
        for s in course.session_ids:
            types.append(s.type)
        
        return ', '.join(set(types))
    
    def get_invoice_address(self, cr, uid, ids, context=None):
        ''
        address = ''
        course = self.browse(cr, uid, ids, context)[0]
        if course.invoice_to_contact and course.student_id.contact_id:
            a_id = course.student_id.contact_id.address_get()['default']
            if a_id:
                a = self.pool.get('res.partner.address').browse(cr, uid, [a_id])[0]
                address = a.name_get()[0][1]
        else:
            address = course.student_id.address
            
        return address
    
    _rec_name = 'id'
    _columns = {
       'session_ids' : fields.many2many('language.school.session', 'language_school_course_session', 'course_id','session_id', 'Sessioni'),
       'notes' : fields.text('Note'),
       'student_id' : fields.many2one('language.school.alia.student', 'Studente'),# TODO on delete CASCADE
       'start_date' : fields.function(_start_date, type='date', store=False, method=True, string='Inizio corso'),
       'end_date' : fields.function(_end_date, type='date', store=False, method=True, string='Fine corso'),
       'hours' : fields.function(_count_hours, type='integer', store=False, method=True, string='Totale ore'),
       'level_in' : fields.many2one('language.school.course.level', 'Livello ingresso'),
       'level_out' : fields.many2one('language.school.course.level', 'Livello raggiunto'),
       'level_next' : fields.many2one('language.school.course.level', 'Livello consigliato'),
       'cfu' : fields.integer('CFU'),
       'individual_hours' : fields.function(_individual_hours, type='integer', store=False, method=True, string='Ore lezione individuale'),
       'stay_ids' : fields.one2many('language.school.stay', 'course_id', 'Permanenze', ondelete='cascade'),
       'fee_ids' : fields.one2many('language.school.course.fee', 'course_id', 'Costi', ondelete='cascade'),
       'total_amount' : fields.function(_total_amount, type='float', store=False, method=True, string='Totale dovuto'),
       'invoice_to_contact' : fields.boolean('Fattura ente di provenienza'),
       'proforma_sent_date' : fields.date('Invio proforma'),
       'lodge_confirm_sent_date' : fields.date('Conferma alloggio'),
    }
language_school_course()


class language_school_alia_student_(osv.osv):
    """Maybe res_contact should be extended instead of writing such a model
    from scratch...

    """
    _name = 'language.school.alia.student'
    _inherit = 'language.school.alia.student'
    _description = 'ALIA students'
   
    def _is_italian(self, cr, uid, ids, field_name, arg, context):
        'function field which checks if student country is Italy'
        res = dict.fromkeys(ids, False)
        for contact in self.browse(cr, uid, ids, context):
            it_id = self.pool.get('res.country').search(cr, uid, [('code', '=', 'IT')])[0]
            it = self.pool.get('res.country').browse(cr, uid, [it_id])[0]
            if contact.country_id == it:
                res[contact.id] = True
        return res

    def _is_italian_search(self, cr, uid, obj, name, args, context=None):
        """This function is invoked when views have a 'domain' field to filter 
        results. Check language_school_student_view.xml
        
        """
        want_italians = False
        for arg in args:
            if arg[0] != 'italian':
                continue
            
            if arg[1] == '=':
                want_italians = arg[2]
            elif arg[1] == '!=':
                want_italians = not arg[2]
        
        check_op = '!='
        if want_italians:
            check_op = '='
        
        # get ITALY object id
        country = self.pool.get('res.country').search(cr, uid, [('code', '=', 'IT')])[0]
        cr.execute('select id from language_school_alia_student where country_id %s %d' % (check_op, country))
        res = cr.fetchall()
        if not len(res): 
            return [('id','=','0')]

        return [('id','in',map(lambda x:x[0], res))] 

    def _last_course_date(self, cr, uid, ids, field_name, arg, context):
        'function field which returns the date of the last course attended'
        res = dict.fromkeys(ids, None)
        for student in self.browse(cr, uid, ids, context):
            if student.course_ids:
                course = student.course_ids[-1]
                res[student.id] = course.end_date
        return res
    
    def name_get(self, cr, user, ids, context={}):
        'return "name last_name" as name for the object'
        if not len(ids):
            return []
        result = []
        for student in self.read(cr, user, ids, ['name','last_name']):
            name = student.get('name', '')
            last_name = student.get('last_name', '')
            result.append((student['id'], "%s %s" % (name, last_name)))
        return result
    
    def name_search(self, cr, user, name='', args=None, operator='ilike',
            context=None, limit=80):
        'support searches for both name and last name'
        if not args:
            args=[]
        if not context:
            context={}
        ids = False
        if len(name) == 2:
            ids = self.search(cr, user, ['|', ('name', 'ilike', name),('last_name', 'ilike', name)] + args,
                    limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, ['|', ('name', operator, name),('last_name', operator, name)] + args,
                    limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    _columns = {
        'name': fields.char('Nome', size=30),
        'last_name': fields.char('Cognome', size=30, required=True),
        'mobile1':fields.char('Cellulare 1',size=30),
        'telephone1':fields.char('Telefono 1',size=30),
        'address':fields.char('Indirizzo',size=120),
        'fax':fields.char('Fax',size=30),
        'website':fields.char('Website',size=120),
        'country_id':fields.many2one('res.country', u'Nazionalità', required=True),
        'birthdate':fields.date('Data di Nascita'),
        'sex':fields.selection([('male','Maschio'),('famale','Femmina')], 'Sesso', size=30),
        'email': fields.char('E-Mail', size=240),
        'skype_id' : fields.char('Skype Id', size=64),
        'note' : fields.text('Note'),
        'active' : fields.boolean('Attivo'),
        'academic_student' : fields.boolean('Accademico'),
        'italian' : fields.function(_is_italian, type='boolean', store=False, fnct_search=_is_italian_search, method=True, string='Studente Italiano'),
        'contact_id' : fields.many2one('res.partner', u'Ente di provenienza'),
        'course_ids' : fields.one2many('language.school.course', 'student_id', 'Corsi tenuti'),
        'voucher_req_ids' : fields.one2many('language.school.voucher.request', 'student_id', 'Voucher'),
        'block_newsletter' : fields.boolean('Blocca newsletter'),
        'last_course_date' : fields.function(_last_course_date, type='date', store=False, fnct_search=None, method=True, string='Fine ultimo corso'),
    }
    
    _defaults = {
        'active' : lambda *a: True,
        'block_newsletter' : lambda *a: False,
    }
language_school_alia_student_()


class language_school_course_level_(osv.osv):
    """The global level of the course
    
    """
    _name = 'language.school.course.level'
    _description = 'Common European Framework of Reference'

    _columns = {
        'name' : fields.char('Nome livello', size=20, required=True),
        'description' : fields.text('Descrizione'),
        'session_in' : fields.one2many('language.school.session', 'level_in', 'Sessioni livello ingresso'),
        'session_out' : fields.one2many('language.school.session', 'level_out', 'Sessioni livello uscita'),
    }
language_school_course_level_()


class language_school_session_(osv.osv):
    """A session is a set of scheduled lessons attended by students
    
    """
    _name = 'language.school.session'
    _inherit = 'language.school.session'
    _description = "Students' activity"
    
    TYPES = [
        ('intensivo', 'Intensivo'),
        ('semintensivo', 'Semintensivo'),
        ('ordinario', 'Ordinario'),
        ('individuale', 'Individuale')
    ]
    
    _columns = {
       'name' : fields.char('Descrizione', size=30, required=True),
       'type' : fields.selection(TYPES, 'Frequenza', required=True),
       'teacher_id' : fields.many2one('res.partner.contact', 'Docente'),
       'start_date' : fields.date('Data inizio', required=True), 
       'end_date' : fields.date('Data fine', required=True),
       'level_in' : fields.many2one('language.school.course.level', 'Livello ingresso'),
       'level_out' : fields.many2one('language.school.course.level', 'Livello previsto'),
       'hours' : fields.integer('Durata ore'),
       'description' : fields.text('Note'),
       'cost' : fields.float('Costo'),
       'course_ids' : fields.many2many('language.school.course', 'language_school_course_session', 'session_id', 'course_id', 'Corsi'),
    }
    
    _defaults = {
        'hours' : lambda *a: 0,
    }
language_school_session_()


class language_school_teacher(osv.osv):
    """Extends partner contacts to support teachers"""
    _name = 'res.partner.contact'
    _inherit = 'res.partner.contact'
    _description = 'Custom base contact representing a teacher'

    def _is_teacher(self, cr, uid, ids, field_name, arg, context):
        'Teachers are contacts related to at least one course session'
        teachers = dict.fromkeys(ids, False)
        for contact in self.browse(cr, uid, ids, context):
            if contact.session_ids:
                teachers[contact.id] = True
        return teachers
    
    def _is_teacher_search(self, cr, uid, obj, name, args, context=None):
        'filter teachers inside views'
        want_teachers = False
        for arg in args:
            if arg[0] != 'teacher':
                continue
            
            if arg[1] == '=':
                want_teachers = arg[2]
            elif arg[1] == '!=':
                want_teachers = not arg[2]
        
        check_op = 'not in'
        if want_teachers:
            check_op = 'in'
        
        contact_ids = self.pool.get('res.partner.contact').search(cr,uid,[])
        contacts = self.browse(cr, uid, contact_ids, context)
        teacher_ids = [x.id for x in contacts if x.session_ids]
        
        return [('id',check_op, teacher_ids)]

    _columns = {
        'teacher' : fields.function(_is_teacher, type='boolean', store=False, fnct_search=_is_teacher_search, method=True, string='Insegnante', help=_("A contact becomes a teacher when associated with a course session")),
        'session_ids' : fields.one2many('language.school.session', 'teacher_id', 'Sessioni tenute'),
        'skype_id' : fields.char('Skype Id', size=64),
        'fax':fields.char('Fax',size=30),
        'address':fields.char('Indirizzo',size=120),
        'note' : fields.text("Note"),
    }
language_school_teacher()


class language_school_course_fee_type(osv.osv):
    """A course may have some fees (taxes, lodge fees, etc).
    This model represents fee types
    
    """
    _name = 'language.school.course.fee.type'
    _description = 'Tipologia costi'

    _columns = {
        'name' : fields.char('Descrizione', size=50, required=True),
        'course_fee' : fields.one2many('language.school.course.fee', 'name', 'Costi'),
        'amount' : fields.float('Importo'),
    }
language_school_course_fee_type()


class language_school_course_fee(osv.osv):
    """
    """
    _name = 'language.school.course.fee'
    _description = 'Costi'
    
    def onchange_course_fee(self, cr, uid, ids, name):
        fee_type = self.pool.get('language.school.course.fee.type').browse(cr,uid, name)
        
        result = {
            'value': {
                'amount': fee_type.amount,
            }
        }
        
        return result

    _columns = {
        'name' : fields.many2one('language.school.course.fee.type', 'Dettaglio', required=True),
        'amount' : fields.float('Importo'),
        'course_id' : fields.many2one('language.school.course', 'Corso'),
    }
    
    _defaults = {
        'amount' : lambda *a : 0.0,
    }
language_school_course_fee()


class language_school_stay(osv.osv):
    """Some students need a lodge to live in during the course.
    This model keeps track of the lodge and the period she'll stay
    
    """
    _name = 'language.school.stay'
    _description = 'Permanenze'
            
    def name_get(self, cr, user, ids, context={}):
        'Return start_date/end_date string'
        import time
        
        res = []
        for rec in self.read(cr, user, ids, ['start_date','end_date']):
            start_date = time.strftime("%d/%m/%Y", time.strptime(rec['start_date'], "%Y-%m-%d"))
            end_date = time.strftime("%d/%m/%Y", time.strptime(rec['end_date'], "%Y-%m-%d"))
            name = '%s - %s' % (start_date, end_date)
            res.append( (rec['id'],name) )
        return res
    
    _columns = {
        'start_date' : fields.date('Data arrivo'),
        'end_date' : fields.date('Data partenza'),
        'lodge_id' : fields.many2one('res.partner', 'Alloggio', required=True, ondelete="cascade"),
        'course_id' : fields.many2one('language.school.course', 'Corso'),
    }
language_school_stay()


class language_school_voucher_request(osv.osv):
    """DRAFT
    
    """
    _name = 'language.school.voucher.request'
    _description = 'Richiesta Voucher'
    
    _columns = {
        'name' : fields.many2one('language.school.voucher', 'Nome voucher'),
        'request_date' : fields.date('Data richiesta'),
        'student_id' : fields.many2one('language.school.alia.student', 'Studente'),
    }
    
    _defaults = {
        'request_date': lambda *a:time.strftime('%Y-%m-%d'),
    }
language_school_voucher_request()


class language_school_voucher(osv.osv):
    """DRAFT
    
    """
    _name = 'language.school.voucher'
    _description = 'Voucher'
    
    _columns = {
        'name' : fields.char('Nome identificativo', size=30, required=True),
        'desc' : fields.text('Descrizione'),
        'request_ids' : fields.one2many('language.school.voucher.request', 'name', 'Richieste'),
    }
language_school_voucher()

