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
import language_school
import language_school_pem

# this is a dirty workaround to fix report templates locale settings
import locale
locale.setlocale(locale.LC_ALL, 'it_IT')