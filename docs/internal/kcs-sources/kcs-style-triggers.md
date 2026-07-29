# Plesk KCS Style Triggers

Status: reviewable Markdown snapshot; the public support article is the source
of truth.

- Canonical source:
  <https://support.plesk.com/hc/en-us/articles/12378148057495-KCS-Style-triggers>
- Source role: normative Plesk trigger and source-markup reference.
- Captured: 2026-07-22 from the operator-provided text export.
- Export filename: `KCS Style Triggers.txt` (not tracked).
- Export SHA-256:
  `450cd5038c51d969ecf1639187f55fe89ae20bac5955fb4f31944062bbf696fd`.

The source image is intentionally omitted. When this snapshot and the public
article differ, use the public article and refresh this file before changing
runtime behavior.

**Note:** After all the triggers you should add a 'space'

```
1. C:\>
```

C:\> "%plesk\_bin%\dbclient.exe" --direct-sql --sql="SELECT displayName FROM
domains" > domains.txt
C:\> for /f "skip=1" %i in (domains.txt) do "%plesk\_dir%\bin\repair.exe" --reconfigure-web-site
-web-site-name %i
C:\> "%plesk\_dir%\bin\repair.exe" --synchronize-protected-directories-storage
C:\> "%plesk\_dir%\bin\repair.exe" --repair-all-webspaces-security

```
2. PS
```

PS foreach ($i in (get-content .\clietns.txt))
{
$cr\_date = ($i -split "\s+")[0];
$login = ($i -split "\s+")[1];
& $env:plesk\_bin\dbclient.exe --direct-sql --sql="update clients set cr\_date='$cr\_date'
where login='$login'";
}.

```
3. Note: 
```

**Note:** This operation requires your patience.

```
4. #
```

# service network status
Configured devices:
lo eth0
Currently active devices:
lo eth0

# service network status
# service network restart
# service network status

```
5. Warning:
```

**Warning:** This may destroy your Plesk. Be careful.

```
6. MYSQL_WIN:
```

MYSQL\_WIN: mysql> update domains set name='example.com' where name='example.com';
Query OK, 0 rows affected (0.00 sec)
Rows matched: 1 Changed: 0 Warnings: 0

```
7. MYSQL_LIN:
```

MYSQL\_LIN: mysql> update domains set name='example.com' where name='example.com';
Query OK, 0 rows affected (0.00 sec)
Rows matched: 1 Changed: 0 Warnings: 0

```
8. PLESK_ERROR:  - for Plesk errors that have pink background in Plesk(mail errors, update errors in Plesk and etc)
```

PLESK\_ERROR: Error: Let's Encrypt SSL certificate installation failed: Challenge
marked as invalid. Details: Could not connect to example.com

PLESK\_ERROR: mailmng failed: mailmng: execve failed for /usr/local/psa/admin/sbin/mailmng:
Permission denied
System error 13: Permission denied
0: Manager.php:186
mail\_Manager->callMailMngWithException(string 'features')
1: Manager.php:152
mail\_Manager->getFeatures()
2: Features.php:53
mail\_Server\_Features->loadFeatures()
3: AbstractFeatures.php:23
mail\_Server\_AbstractFeatures->\_\_construct()

```
9. PLESK_WARN:  - for Plesk warning that have yellow background in Plesk
```

PLESK\_WARN: For security reasons, we recommend that you protect data contained
in backups. Please go to [Backup Settings](https://example.com:8443/smb/settings/tools-proxy?url=/admin/backup/settings&returnAction=tools) and
update backup security settings.

Snapshot sanitization note: the source export used a non-reserved example host;
this tracked copy uses the documentation domain `example.com`.

```
10. PLESK_INFO:  - for Plesk errors that have white/gray background in Plesk(MySQL access denied errors and etc)
```

PLESK\_INFO: ERROR: PleskFatalException
Unable to connect to database: saved admin password is incorrect.
0: common\_func.php3:93
psaerror(string 'Unable to connect to database: saved admin password is incorrect.')
1: auth.php3:127

```
11. CONFIG_TEXT:  - for any configurations that should be added to the file and etc.
```

CONFIG\_TEXT: /\* margin: -5px!important; \*/
border: 1px solid lightgray;
min-width:670px;
max-width:1000px;
font-family: 'Open Sans', arial;
}

```
12. Add image preview that will be shown in full size by click:
```

```
<img src="link/to/image/78594.png" alt="Indexable text here" class="resizable"/>
- add image preview that will be shown in full size by click.
ALT property adds searchable/indexable text to the image, can be used to shorten articles with images. Otherwise, set alt="" (empty).
```

[Source image omitted from Markdown snapshot.]

```
13. For an accordion:
```

```
<div class="accordion__item">
<div class="accordion__item-title">
<strong>Accordion item</strong>
</div>
<div class="accordion__item-content">
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</div>
</div>
```

*Click on a section to expand*

**Accordion item**

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex
ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate
velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat
cupidatat non proident, sunt in culpa qui officia deserunt mollit anim
id est laborum.

```
14. For tabs:
```

```
<div class="tabs-content">
<div id="1" class="tab-header current">Header of the Tab1</div>
<div id="content1" class="tab-content active">
Content of the Tab 1
</div>
<div id="2" class="tab-header">Header of the Tab2</div>
<div id="content2" class="tab-content">
Content of the Tab 2
</div>
<div id="3" class="tab-header">Header of the Tab3</div>
<div id="content3" class="tab-content">
Content of the Tab 3
</div>
</div>
```

Header of the Tab1

### You're on tab 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec blandit
laoreet enim, quis eleifend sapien commodo in. Curabitur eu lectus quam,
in pulvinar dui. Ut sit amet eros leo, nec rhoncus nulla. Mauris tempor
volutpat lacinia. Cras facilisis sem a nunc consectetur non molestie
purus imperdiet. Proin sit amet neque nisi, in porttitor tellus. Aliquam
dolor nulla, iaculis ut pretium in, pretium id lorem.

Header of the Tab2

### You're on tab 2

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec blandit
laoreet enim, quis eleifend sapien commodo in. Curabitur eu lectus quam,
in pulvinar dui. Ut sit amet eros leo, nec rhoncus nulla. Mauris tempor
volutpat lacinia. Cras facilisis sem a nunc consectetur non molestie
purus imperdiet. Proin sit amet neque nisi, in porttitor tellus. Aliquam
dolor nulla, iaculis ut pretium in, pretium id lorem.

Header of the Tab3

### You're on tab 3

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec blandit
laoreet enim, quis eleifend sapien commodo in. Curabitur eu lectus quam,
in pulvinar dui. Ut sit amet eros leo, nec rhoncus nulla. Mauris tempor
volutpat lacinia. Cras facilisis sem a nunc consectetur non molestie
purus imperdiet. Proin sit amet neque nisi, in porttitor tellus. Aliquam
dolor nulla, iaculis ut pretium in, pretium id lorem.

```
15. For text that should not be copied:
```

```
<span class="unselectable">text that should not be copied</span> - for any outputs in shell or command prompt.
```

# service network status
(cannot be copied) Configured devices:
lo eth0
Currently active devices:
lo eth0

```
16. Tables examples
```

|  | Sunday | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lawrence Scott | 8:00 AM | -- | -- | 8:00 AM | -- | 5:00 PM | 8:00 AM |
| Jane Medina | -- | 5:00 PM | 5:00 PM | -- | 9:00 AM | -- | -- |
| Billy Mitchell | 9:00 AM | -- | -- | -- | -- | 2:00 PM | 8:00 AM |
| Beverly Reid | -- | 5:00 PM | 5:00 PM | -- | 9:00 AM | -- | -- |
| Tiffany Wade | 8:00 AM | -- | -- | 8:00 AM | -- | 5:00 PM | 8:00 AM |
| Sean Adams | -- | 5:00 PM | 5:00 PM | -- | 9:00 AM | -- | -- |
| Rachel Simpson | 9:00 AM | -- | -- | -- | -- | 2:00 PM | 8:00 AM |
| Mark Salazar | 8:00 AM | -- | -- | 8:00 AM | -- | 5:00 PM | 8:00 AM |

| Module name | Explanation |
| --- | --- |
| authnz\_ldap | was used in Apache 2.2, removed in Apache 2.4 |
| ldap | was used in Apache 2.2, removed in Apache 2.4 |
| authn\_default | was used in Apache 2.2, removed in Apache 2.4 |
| authz\_default | was used in Apache 2.2, removed in Apache 2.4 |
| disk\_cache | was used in Apache 2.2, renamed to cache\_disk in Apache 2.4 |
| cgi | was used in Apache 2.2, replaced by cgid in Apache 2.4 |
| negotiation | used on deb like systems but not on RedHat based |
| setenvif | used on deb like systems but not on RedHat based |
| dir | used on deb like systems but not on RedHat based |
| autoindex | used on deb like systems but not on RedHat based |
| perl | not installed by default starting from Plesk 12.5. You will see such a message if the destination is higher than 12.5 and a source lower than 12.5 |
| python | not installed by default starting from Plesk 12.5. You will see such a message if the destination is higher than 12.5 and a source lower than 12.5 |
| php5 | not installed by default starting from Plesk 12.5. You will see such a message if the destination is higher than 12.5 and a source lower than 12.5 |

```
17. Internal notes - for leaving hidden notes that will be visible only to agents:
```

```
<div class="internaldata"><p>Your internal note here</p></div>
```

Your internal note here

Note: it's still possible to see these notes by using different
methods (the user can check browser console, or subscribe to
a public article and he'll receive an email update with the note)
- mind what you write there

```
18. Splitter line:
```

```
<hr style="border: none; height: 2px; background-color: #ccc;">
```

---
