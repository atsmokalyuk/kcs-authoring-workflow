# Article Simplification Guide

Status: reviewable Markdown snapshot; the canonical Confluence page is the
source of truth.

- Canonical source:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902677/Article+simplification+guide>
- Source role: supporting polish guidance, lower priority than Article Quality
  Criteria.
- Captured: 2026-07-22 from the operator-provided Confluence export.
- Export filename: `Article+simplification+guide.doc` (not tracked).
- Export SHA-256:
  `a854af6d7e86c04562f4702add55be38a29a64da2d5bb4ad8b33d9e26a190baa`.

Confluence images are intentionally omitted from this text snapshot. Examples
are evidence for review, not automatically executable or safe golden output.
When the snapshot and canonical page differ, use the canonical page.

- [Introduction](#Articlesimplificationguide-Introduction)
- [Best practices](#Articlesimplificationguide-Bestpractices)
  - [Start every solution from beginning](#Articlesimplificationguide-Starteverysolutionfrombeginning)
  - [Give step-by-step and full solution](#Articlesimplificationguide-Givestep-by-stepandfullsolution)
  - [Use screenshots to guide through solution](#Articlesimplificationguide-Usescreenshotstoguidethroughsolution)
  - [Plesk interface before server console](#Articlesimplificationguide-Pleskinterfacebeforeserverconsole)
  - [Service Provider View vs. Power User View](#Articlesimplificationguide-ServiceProviderViewvs.PowerUserView)
  - [Most commonly used resolution steps](#Articlesimplificationguide-Mostcommonlyusedresolutionsteps)

# Introduction

We do have geeky customers, but we also have a lot of clients who are not system administrators and are not common with server management.

This guide describes how to create articles which would be clear for all clients and will make them happy with our Help Center.

Each section describes best practices and provides examples of good and bad articles.

# Best practices

## Start every solution from beginning

To make article helpful its solution must describe where it can be applied.

If you provide shell commands you should explain how to access server over SSH. If you provide database queries you should specify how to access Plesk database and how to create/restore database dump.

The same is valid for different tools like *Plesk Reconfigurator* or *MailEnable Management Console*.

In case you just provide some commands or ask to launch some tool and do not explain how exactly, article will not help, it will just dissatisfy customer and cause new ticket.

It is not needed to describe these in every article, you can use existing articles as reference.

**Good**

[Source image omitted from Markdown snapshot.]

#### Symptoms

Plesk is not accessible and shows errors on login screen:

```
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.sessions' doesn't exist
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.sessioncontexts' doesn't exist
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.servicenodes' doesn't exist
```

#### Cause

Database inconsistency. Some tables in `psa`database are missing

#### Resolution

Restore `psa`database from a backup using article [How to backup/restore a Plesk database dump](https://support.plesk.com/hc/en-us/articles/213904125)

[Source image omitted from Markdown snapshot.]

#### Symptoms

Domains are not working. Apache start from the bash fails with the following error:

```
(98)Address already in use: make_sock: could not bind to address [::]:443 no listening sockets available, shutting down
```

Port may be also 80, 7080, 7081.

#### Cause

Some other process already uses 443 (80) port and Apache cannot bind to it.

#### Resolution

Connect to the server [using SSH.](https://support.plesk.com/hc/en-us/articles/115000172834)

1. Find what service listens 443 port:

   ```
   # netstat -tunap | grep :443
   tcp        0      0 0.0.0.0:443            0.0.0.0:*              LISTEN      484/haproxy
   ```
2. It is not expected that "haproxy" or another service except "apache/httpd" or "nginx" listens to 443 port, so it should be stopped or killed:

   ```
   # service haproxy stop
   ```
3. In case if any other process is running using this port or "apache/httpd" process, it should be killed:

   ```
   # kill -9 484
   ```
4. In case if "nginx" service is using the reported port, try to perform the following:

   ```
   # /usr/local/psa/admin/sbin/nginxmng -d
   # /usr/local/psa/admin/sbin/nginxmng -e
   ```

**Bad**

[Source image omitted from Markdown snapshot.]

#### Symptoms

Plesk is not accessible:

```
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.sessions' doesn't exist
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.sessioncontexts' doesn't exist
ERROR: Zend_Db_Statement_Exception: SQLSTATE[42S02]: Base table or view not found: 1146 Table 'psa.servicenodes' doesn't exist
```

#### Cause

Database inconsistency.

#### Resolution

Restore psa from the backup.

[Source image omitted from Markdown snapshot.]

#### Symptoms

Apache fails with error:

```
(98)Address already in use: make_sock: could not bind to address [::]:443 no listening sockets available, shutting down
```

Port may be also 80, 7080, 7081.

#### Cause

Some other process already uses 443 (80) port and Apache cannot bind to it.

#### Resolution

Kill the found process by netstat utility that using apache port and start apache.

## Give step-by-step and full solution

Every solution should be clear and contain all steps. Each step should be atomic and describe one exact action, next step should follow the previous one.

If custom fix is provided, article should explain how to download this fix and how exactly it can be applied.

In case database queries are used for solution, article should explain how to get the values.

**Good**

[Source image omitted from Markdown snapshot.]

#### Symptoms

Unable to log in to Plesk. The following error is displayed instead of the login screen:

```
ERROR: PleskFatalException
Unable to connect to database: saved admin password is incorrect.
0: common_func.php3:93
psaerror(string 'Unable to connect to database: saved admin password is incorrect.')
1: auth.php3:127
```

OR

```
Access denied for user 'admin'@'localhost' (using password: YES)
```

#### Cause

- The password in `/etc/psa/.psa.shadow`file (which is used to access Plesk database), does not match the admin password in MySQL database.

#### Resolution

1. Connect to the server [using SSH](https://support.plesk.com/hc/en-us/articles/115000172834).
2. Make sure that the option `old-passwords`is not set to 1 in `/etc/my.cnf`file (on Debian based distributions the path is `/etc/mysql/my.cnf`):

   ```
   # grep -ir old-passwords /etc/my*
   #
   ```
3. Obtain the correct Plesk password:

   ```
   # cat /etc/psa/.psa.shadow
   $AES-128-*****************************************************
   ```
4. Try connecting to the MySQL database and update admin password:

   ```
   # MYSQL_PWD=`cat /etc/psa/.psa.shadow` mysql -u admin mysql
   mysql> UPDATE mysql.user SET Password=PASSWORD('$AES-128-***') WHERE User='admin';
   ```

   **Note:**If you are unable to connect, add `skip-grant-tables string` in the `/etc/my.cnf`file (on Debian based distributions the path is `/etc/mysql/my.cnf):`

   ```
   # cat /etc/my.cnf
   ...
   [mysqld]
   skip-grant-tables
   ...
   ```

   restart MySQL server and update the admin password:

   ```
   # service mysqld restart (for CentOS)
   # service mysql restart (for Debian/Ubuntu)
   # mysql -uadmin mysql
   mysql> UPDATE mysql.user SET Password=PASSWORD('$AES-128-***') WHERE User='admin';
   ```

   After that, do not forget to remove `skip-grant-tables`and restart MySQL service.
5. Update the password for Plesk using the `ch_admin_passwd`utility:

   ```
   # /usr/local/psa/bin/admin --show-password
   plesk_password
   # export PSA_PASSWORD=password
   # /usr/local/psa/admin/bin/ch_admin_passwd
   ```

**Bad**

[Source image omitted from Markdown snapshot.]

#### Symptoms

Unable to log in to Plesk. The following error is displayed instead of the login screen:

```
ERROR: PleskFatalException
Unable to connect to database: saved admin password is incorrect.
0: common_func.php3:93
psaerror(string 'Unable to connect to database: saved admin password is incorrect.')
1: auth.php3:127
```

OR

```
Access denied for user 'admin'@'localhost' (using password: YES)
```

#### Cause

- The password in `/etc/psa/.psa.shadow`file (which is used to access Plesk database), does not match the admin password in MySQL database.

#### Resolution

1. Make sure that the option `old-passwords`is not set to 1 in `my.cnf`
2. Obtain the correct Plesk password:

   ```
   # cat /etc/psa/.psa.shadow
   $AES-128-*****************************************************
   ```
3. Try connecting to the MySQL database and update admin password:

   ```
   # MYSQL_PWD=`cat /etc/psa/.psa.shadow` mysql -u admin mysql
   mysql> UPDATE mysql.user SET Password=PASSWORD('$AES-128-***') WHERE User='admin';
   ```

   **Note:**If you are unable to connect, add `skip-grant-tables string` in the `my.cnf`

   restart MySQL server and update the admin password:

   ```
   mysql> UPDATE mysql.user SET Password=PASSWORD('$AES-128-***') WHERE User='admin';
   ```

   After that, do not forget to remove `skip-grant-tables`and restart MySQL service.
4. Update the password for Plesk using the `ch_admin_passwd`utility:

   ```
   # /usr/local/psa/bin/admin --show-password
   plesk_password
   # export PSA_PASSWORD=password
   # /usr/local/psa/admin/bin/ch_admin_passwd
   ```

## Use screenshots to guide through solution

Not every client is common with Plesk or other software UI. If you just describe section names there is a possibility that the necessary section will not be found. Also interface can have a lot of different tabs and buttons.

When the screenshot is provided it is easier to find the necessary button or tab and apply the solution. Also your article will help clients to learn Plesk and get more experienced.

It is not needed to give a full screen screenshot, part of the page is enough. Highlight interface elements which are described in resolution. Remember that specifying of full path is still needed.

**Good**

[Source image omitted from Markdown snapshot.]

#### Question

How to secure webmail using Let's Encrypt in Plesk Onyx?

#### Answer

This feature is available in [Let's Encrypt 2.1.0](https://ext.plesk.com/packages/f6847e61-33a7-4104-8dc9-d26a0183a8dd-letsencrypt) extension which was released on May 19. Make sure that it is [updated/installed](https://support.plesk.com/hc/en-us/articles/115000159173) in **Plesk > Extensions**

Perform the following instructions:

1. Make sure that there is no wildcard domain like '\*.[example.com](http://example.com) ' or '[webmail.example.com](http://webmail.example.com)' present on subscription in Plesk(**Plesk > Domains**) that is required to secure. Remove it if found.
2. Obtain a new Let's Encrypt certificate in **Domains >** [example.com](http://example.com)  **> Let's Encrypt**
   Select **Secure webmail on this domain**and **Include a "www"...**if your domain has configured www prefix. Click **Install**

   [Source image omitted from Markdown snapshot.]
3. It is also possible to secure webmail using existing Let's Encrypt certificate in **Domains >** <http://example.com>  **> SSL Certificates**clicking **Secure Webmail**

   [Source image omitted from Markdown snapshot.]

**Bad**

[Source image omitted from Markdown snapshot.]

#### Question

How to secure webmail using Let's Encrypt in Plesk Onyx?

#### Answer

This feature is available in [Let's Encrypt 2.1.0](https://ext.plesk.com/packages/f6847e61-33a7-4104-8dc9-d26a0183a8dd-letsencrypt) extension which was released on May 19. Make sure that it is [updated/installed](https://support.plesk.com/hc/en-us/articles/115000159173) in **Plesk > Extensions**

Perform the following instructions:

1. Make sure that there is no wildcard domain like '\*.[example.com](http://example.com/)' or '[webmail.example.com](http://webmail.example.com/)' present on subscription in Plesk(**Plesk > Domains**) that is required to secure. Remove it if found.
2. Obtain a new Let's Encrypt certificate in **Domains >** [**example.com**](http://example.com/) **> Let's Encrypt**
   Select **Secure webmail on this domain**and **Include a "www"...**if your domain has configured www prefix. Click **Install**
3. It is also possible to secure webmail using existing Let's Encrypt certificate in **Domains >** [**example.com**](http://example.com/) **> SSL Certificates**  clicking **Secure Webmail**

## Plesk interface before server console

Using actions from Plesk UI is much safer than using commands from server console and it helps customers to better know Plesk.

If steps described in article can be done through Plesk UI you should specify them first and add screenshots.

In case you want to extend article and describe how the same can be done from server console add these instructions after.

If the only way to achieve the result is SSH consider to submit a feature request to R&D.

## Service Provider View vs. Power User View

Whenever you receive a ticket with server which has Power User View only (e.g. Web Admin license is installed) and you use an article which describes resolution from Plesk Interface you need to make sure that this article is fully applicable to Power User View as well. In case it is not you should separately document resolution for Power User View in this article.

Do not do it for every article. Do it only for cases when client has Power User View only.

## Most commonly used resolution steps

Connect to the server [via SSH](https://support.plesk.com/hc/en-us/articles/115000172834)

[Connect to the server](https://support.plesk.com/hc/en-us/articles/115000172834) [via RDP](https://support.plesk.com/hc/en-us/articles/360000471413)

Login to [Plesk database](https://support.plesk.com/hc/en-us/articles/213928465)

Upgrade Plesk [to the latest version](https://support.plesk.com/hc/en-us/articles/213408749)

Restore `psa`database from a backup using article [How to backup/restore a Plesk database dump](https://support.plesk.com/hc/en-us/articles/213904125)

[Install <some> extension.](https://support.plesk.com/hc/en-us/articles/115000180213)

[Update <some\_extension> extension.](https://support.plesk.com/hc/en-us/articles/115000159173)
