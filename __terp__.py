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
{
    "name" : "Language School Management",
    "author" : "Evonove srl",
    "website" : "www.evonove.it",
    "description" : "Custom CRM for ALIA",
    "version" : "0.1.0",
    "license" : "GPL-3",
    "depends" : ["base","base_contact","poweremail","report_openoffice"],
    "update_xml" : [
        'security/language_school_security.xml',
        #'security/ir.model.access.csv',
        'data/language.school.course.level.csv',
        'data/data.xml',
        'report/course_reports.xml',
        'report/poweremail_templates.xml',
        'language_school_view.xml',
        'language_school_pem_view.xml',
        'language_school_lodge_view.xml',
        'language_school_student_view.xml',
    ],
    'demo_xml': [
        'demo/demo_data.xml',
    ],
    "category" : "Enterprise Specific Modules/Schools",
    "installable": True,
    "active": False,
}
