#!/bin/bash

apt-get install gosa-schema samba samba-doc smbldap-tools python-dev libldap2-dev libsasl2-dev libssl-dev -y
slapcat -n 0 > /tmp/config_orig.ldif
grep -B1000 "dn: cn={2}nis" /tmp/config_orig.ldif | grep -v "dn: cn={2}nis" > /tmp/config_pref.ldif
grep -A1000 "dn: cn={3}" /tmp/config_orig.ldif > /tmp/config_suff.ldif
cat /tmp/config_pref.ldif > /tmp/config.ldif
cat /etc/ldap/schema/gosa/rfc2307bis.ldif | sed -e 's/cn=rfc2307bis/cn={2}rfc2307bis/' -e 's/cn: rfc2307bis/cn: {2}rfc2307bis/' -e '/^#/d' >> /tmp/config.ldif
echo "" >> /tmp/config.ldif
cat /tmp/config_suff.ldif >> /tmp/config.ldif

/etc/init.d/slapd stop
rm -r /etc/ldap/slapd.d/*
slapadd -F /etc/ldap/slapd.d/ -n 0 -l /tmp/config.ldif
chown -R openldap:openldap /etc/ldap/slapd.d/
/etc/init.d/slapd start

rm /tmp/config_*.ldif

cp /usr/share/doc/samba-doc/examples/LDAP/samba.ldif.gz /etc/ldap/schema/
gzip -d /etc/ldap/schema/samba.ldif.gz
cp django.* /etc/ldap/schema/
ldapadd -Q -Y EXTERNAL -H ldapi:/// -f /etc/ldap/schema/samba.ldif
ldapadd -Q -Y EXTERNAL -H ldapi:/// -f /etc/ldap/schema/django.ldif

DC=$(ldapsearch -x -s base namingContexts -LLL | grep namingContexts | sed -e 's/namingContexts: //')
ADMIN="cn=admin,${DC}"

NETSID=$(net getlocalsid | awk -F ': ' '{print $2}')

cat overlays.ldif | sed -e "s/@DOMAIN@/${DC}/" -e "s/@ADMIN@/${ADMIN}/" > /tmp/overlays.ldif
cat ou.ldif | sed -e "s/@DOMAIN@/${DC}/" -e "s/@ADMIN@/${ADMIN}/" -e "s/@NETSID@/${NETSID}/" > /tmp/ou.ldif
ldapadd -Y EXTERNAL -H ldapi:/// -f "/tmp/overlays.ldif"
ldapadd -x -D cn=admin,${DC} -W -H ldapi:/// -f "/tmp/ou.ldif"

rm /tmp/overlays.ldif /tmp/ou.ldif

