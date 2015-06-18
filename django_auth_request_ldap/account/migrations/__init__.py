# First of all.. THIS IS A VERY UGLY HACK.
#  there, it is said.

# Seeing we are doing something out-of-the-ordinary by hooking up a LDAP
#  back-end to django's interface.. we'll have to 'work around' some issues.
# First of all, django creates a fkey between it's admin log (admin.LogEntry)
#  and whatever model is currently installed. Now we can 'avoid' most of the
#  joining of tables by creatively hacking LogEntry's select_related.. and
#  this will work, however, during initial migrations you will get a metric
#  cowube of errors.
# So, in comes the new migration system, which most people don't realise how
#  much 'fun' you can have with it.. and we have some fun with it:

# - We ensure we have an initial migration that django.contrib.admin relies upon
#  - This initial migration 'fakes' an account.User model, so that any FK
#    constraints set during creation will not fail.
# - We also have a migration that 'depends' on django.contrib.admin's initial
#   migration, to revert the fk constraint by faking the following:
#  - We rename the 'user' field to 'user_id'
#  - We change the 'user_id' field from a ForeignKey to an IntegerField.
#  While this seems elaborate, simply changing from ForeignKey to IntegerField
#   will also implicitly rename the 'user_id' database field to 'user'.. as
#   ForeignKey appends the _id part behind it. by doing the rename first we
#   will ensure that it renames from 'user_id' to 'user_id_id' back to 'user_id'
