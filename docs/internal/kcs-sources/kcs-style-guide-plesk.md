# Plesk KCS Style Guide

Status: reviewable Markdown snapshot; the canonical Confluence page is the
source of truth.

- Canonical source:
  <https://webpros.atlassian.net/wiki/spaces/SOLUS/pages/3649045319/KCS+Style+Guide>
- Source role: Plesk-specific normative style and markup rules.
- Captured: 2026-07-22 from the operator-provided Confluence export.
- Export filename: `KCS+Style+Guide (1).doc` (not tracked).
- Export SHA-256:
  `cc940c94a94d7a6c18561eb36ba4e9af4e0cebd186d8acd5f30e12b8d774bbb4`.

Confluence images are intentionally omitted from this text snapshot. When the
snapshot and canonical page differ, use the canonical page and refresh this
file before changing runtime behavior.

- [What is KCS Style Guide?](#KCSStyleGuide-WhatisKCSStyleGuide?)
- [Article structure requirements](#KCSStyleGuide-Articlestructurerequirements)
  - [Article title (subject)](#KCSStyleGuide-Articletitle(subject))
  - [Article environment](#KCSStyleGuide-Articleenvironment)
  - [Article body](#KCSStyleGuide-Articlebody)
    - [Technical articles](#KCSStyleGuide-Technicalarticles)
    - [How-to articles](#KCSStyleGuide-How-toarticles)
  - [Article labels](#KCSStyleGuide-Articlelabels)
- [Attaching files and screenshots](#KCSStyleGuide-Attachingfilesandscreenshots)
- [Content formatting](#KCSStyleGuide-Contentformatting)

# What is KCS Style Guide?

It is a block of rules that helps to make an article good looking, simple, easy to understand and apply.

# Article structure requirements

Any article has the following parts:

- Title
- Environment
- Body
- Labels

Each part of the article structure has its own requirements.

## Article title (subject)

Article’s subject should contain all required information to understand that this article may be helpful in customer’s issue. The first part of article's title should contain what action is not possible to do. For example, in upgrade issues, it should be like **Unable to upgrade Plesk**. The second part of article’s title should be separated with a colon and should contain an error that is found or shown during an upgrade, of course, if it present. For example: **ERROR while trying to check the hostname**. So the complete name of the article in such case should be **Unable to upgrade Plesk: ERROR while trying to check the hostname**.

[Source image omitted from Markdown snapshot.]

Plesk login fails: DB query failed: Unknown error

Error when deleting an account: Deletion of last account member is forbidden

Article’s title should be short:

**BAD:** When I try to create new user account on Plesk 12.5 for Windows I receive error: 'No such file or directory'

**GOOD:** Cannot create user account: No such file or directory

Do not add dots to the end of article’s title. Avoid using brackets and quotes in the subject if these symbols are not present in the error message.

In How-to articles title should contain a brief version of the question.

[Source image omitted from Markdown snapshot.]

How to create a user account (using the RPC API) with access to only one subscription?

How to disable recursive DNS queries?

Does Plesk support PHP 5.4?

## Article environment

Article environment is represented by **Applicable to** section of the article.

This section is generated and styled automatically based on **Environmental labels**.

The platform is mandatory, all the labels without platform will be removed.

[Source image omitted from Markdown snapshot.]

Such labels should contain the ticket’s environment and a platform like the following:

- Plesk for Windows
- Plesk for Linux
- Plesk Obsidian for Windows
- Plesk Obsidian for Linux
- Plesk Onyx 17.8 for Windows
- Plesk Onyx 17.8 for Linux
- and etc for other Plesk versions.

## Article body

Article body contains the main content of the article: issue or question description, cause (if any) and resolution or answer.

It must contain a corresponding sections which makes it easy to understand.

### Technical articles

These articles have 3 sections:

- **Symptoms** – the section where all errors, behaviors, situations provided by the customer and found during an investigation are described. In general, symptoms are helping to determine if this article is suitable for the issue you are experiencing with. Basically, symptoms section is based on a customer’s words with small cosmetic corrections and our findings during an issue investigation.
- **Cause** – section with an explanation why this happens in this way, what is wrong and any description regarding this behavior.
- **Resolution** – the section where any workaround or resolution should be provided, in other words how to fix the initial symptom or what is possible to do. Please note, that any explanations why this happens should be provided in Cause section. Here should be steps how to resolve the issue. In general, it should be a reply, taken from the ticket with corrections provided below.

### How-to articles

These articles have 2 sections:

- **Question** – section, where any behavior is described with a question how to change it, why this happens or how to configure some service/perform task.
- **Answer** – section, with an explanation, steps how to do it.

Technical articles with errors cannot be ‘How to’ articles and should contain **Symptoms/Cause/Resolution** structure.

If it is required to use ‘How to’ article in a technical article, it may be linked in Resolution section.

## Article labels

Labels help to:

- find the required article faster
- identify the Plesk version or platform for the client
- notice support drivers and transfer it to R&D for improvements

[Source image omitted from Markdown snapshot.]

Every article must contain one of the below labels used to identify the type of article:

- *kb: bug* - articles about product bugs that haven't been fixed yet. Tag is set automatically by the script when Jira ID is mentioned in the article and replacing tags kb: technical or *kb: how-to*.
- *kb: fixed* - articles about product bugs that were mentioned in [Release Notes](https://docs.plesk.com/release-notes/obsidian/change-log/) as fixed.
- *kb: tools* - articles that are describing processes or how to use utilities, are often used as a separate step in other articles.
- *kb: auxiliary* - general articles (usually "how-to" ones) that are used as a part of the solution. For example, the customer reports that the extension doesn't work. We have an article, that recommends reinstalling the extension with the reference on [How to manage Plesk extensions (install, disable, remove, update)](https://support.plesk.com/hc/en-us/articles/115000180213). Despite this article doesn't have any symptoms, it describes the process, that helps to fix the initial customer's issue. So [How to manage Plesk extensions (install, disable, remove, update)](https://support.plesk.com/hc/en-us/articles/115000180213) is an auxiliary article.
- *kb: how-to* - technical Question/Answer articles that provide instructions for the particular customers' question. Added automatically when "Q/A" article template is used.
- kb: technical - all Problem/Solutions cases. Added automatically for new articles when "Problem" article template is used.
- kb: security - all Security cases (CVE). Added automatically for new articles when "CVE" article template is used.

The last 2 labels are to be used by engineers, all others shouldn't be touched as they are added automatically.

1. If there is no special label in the article for some reason, add either*kb: how-to*or*kb: technical one*.
2. If you noticed incorrect *kb: how-to*or *kb: technical* label - fix it by yourself.
3. In case *kb: bug, kb: fixed, kb: tools* or *kb: auxiliary* label is already added, don't change/add special tags.

[Source image omitted from Markdown snapshot.]

Labels with technical tags like below should not be touched:

- *FR:\*\*\**
- *DoNotDelete:docref*
- *MT and MG*

[Source image omitted from Markdown snapshot.]

These labels should be added manually to the corresponding article if necessary.

All labels start with “ext: “, for example:

- ext: wptk
- ext: migrator
- ext: acronis
- ext: kolab
- ext: pes
- etc

# Attaching files and screenshots

**Note:** Always attach files only in .zip format for Windows or .tar.gz for Linux.

For attaching files or images, just drag-and-drop and place it on the side needed:

[Source image omitted from Markdown snapshot.]

New window for media management will appear and upload will start (section is available in **Placement > Manage attached media**):

[Source image omitted from Markdown snapshot.]

Copy the URL of the file uploaded and place it in the article as needed.

If the article is published, verify the image is shown in incognito mode (not signed in).

[Source image omitted from Markdown snapshot.]

Screenshots should be created with the help of **Snipping Tool** utility.

After screenshot creation save it as **.png file** and attach it in editor using drag-and-drop.

In case you need to highlight elements on screenshot open it in **Paint**and use figures (boxes and arrows) without fill. Color of borders should be red.

# Content formatting

Text formatting is used to make an article good looking and easy to read.

|  |  |
| --- | --- |
| **Paths** | Path in any GUI (Plesk, Windows, ReoudCube, etc.) must be **bold**. For example:  **Tools & Settings > Server Components > DNS Server** |
| **Buttons and menus** | Name of any button or menu must be **bold**. For example:  **Reread IPs** |
| **Inline command-line utility names, paths** | Inline command-line utility names, paths to any log files/directories or inline commands output should be printed with typescript by using <code></code> tag: `vhostmng.exe`, `/usr/local/psa/bin/admin` |
| **Product names** | Do not highlight product names (Apache/Plesk/Comodo) in any way. They should be in plain text: Plesk, Comodo, Apache. |
| **Windows paths** | When specifying Windows paths, always use `%plesk_dir%`, `%plesk_bin%`, `%plesk_cli%`, `%plesk_vhosts%` and `%windir%` where applicable instead of full paths.  Exception: paths in errors |
| ZenDesk KCS editor supports triggers, which automate article formatting and can be used without editing article’s source code.  It is mandatary to use them when formatting shell output, error messages, etc.  You can see how all triggers work in the [article](https://support.plesk.com/hc/en-us/articles/12378148057495-KCS-Style-triggers)  It must be a space between trigger and text | |
| **Windows Command Prompt** | **Usage:**  `C:\> text here`  **Result:** |
| **Windows PowerShell** | **Usage:**  `PS text here`  **Result:** |
| **Linux shell** | **Usage:**  `# text here`  **Result:** |
| **MySQL queries on Windows** | **Usage:**  `MYSQL_WIN: text here`  **Result:** |
| **MySQL queries on Linux** | **Usage:**  `MYSQL_LIN: text here`  **Result:** |
| **Notes** | **Usage:**  `Note: text here`  **Result:** |
| **Warnings** | **Usage:**  `Warning: text here`  **Result:** |
| **Plesk errors** that have **pink** background in UI(mail errors, update errors and etc) | **Usage:**  `PLESK_ERROR: text here`  **Result:** |
| **Plesk warnings** that have yellow background in UI | **Usage:**  `PLESK_WARN: text here`  **Result:** |
| **Plesk errors and messages** that have **white/gray** background in Plesk(MySQL access denied errors and etc) | **Usage:**  `PLESK_INFO: text here`  **Result:** |
| **Configuration directives and content of logs/config files** | **Usage:**  `CONFIG_TEXT: text here`  **Result:** |
| For accurate article tuning its source code can be edited. It uses standard HTML markdown and can be opened from KCS editor.  For example, <p></p> tags for paragraphs, <ol></ol> for ordered lists, etc. | |
| **Clickable image preview** | Images that require being maximized should have class '**resizable**' assigned in the following way: image-20250314-074136.png There is no need to specify the width and height inside the <img> tag with aforementioned class. By default the image will have width=460, hovering on them will return the hint 'Click to maximize'. On clicking the image the lightbox with the bigger picture will appear. It can be closed either clicking the cross in the upper right corner, or anywhere on the display.  Aforementioned behavior could be observed in the [following article](https://support.plesk.com/hc/en-us/articles/12377676289815). |
| **Tabs** | ``` <div class="tabs-content">     <div id="1" class="tab-header current">Header of the Tab1</div>     <div id="content1" class="tab-content active">         Content of the Tab 1     </div>     <div id="2" class="tab-header">Header of the Tab2</div>     <div id="content2" class="tab-content">         Content of the Tab 2     </div>     <div id="3" class="tab-header">Header of the Tab3</div>     <div id="content3" class="tab-content">         Content of the Tab 3     </div> </div> ```  **Notes:**   1. There can be as many segments as you need, it is not limited to 2 or 3 tabs only 2. The first (default) tab should be defined like this (note: there should be **only one** default tab):   ``` <div id="1" class="tab-header current">Header of the Tab1</div> <div id="content1" class="tab-content active">         Content of the Tab 1 </div> ```   3. All subsequent tabs can be defined like this:   ``` <div id="<ID>" class="tab-header">Header of the Tab</div> <div id="content<ID>" class="tab-content">         Content of the Tab  </div> ```  **Important:** make sure to replace `id="ID"` and `id="content<ID>"` values with the actual tab’s number, for example:  ``` <div id="2" class="tab-header">Tab number 2</div> <div id="content2" class="tab-content">         Tab number 2's content </div> ```   4. All segments should be wrapped with a single `<div class="tabs-contents"> </div>` 5. As tab’s headers should be as short as possible, it’s recommended to add some heading with `<h3></h3>` |
| **Text spoiler (Expand/Accordion)**  **Note: Use Tabs first** | ``` <div class="accordion__item">     <div class="accordion__item-title">       <strong>Accordion item</strong>     </div>     <div class="accordion__item-content">       <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>     </div> </div> ``` |
| **Tables** | ``` <div class="tabs-content"> <div class="container-table100">   <div class="wrap-table100">     <div class="table100 ver1">       <table data-vertable="ver1">         <thead>           <tr class="row100 head">             <th class="column100 column1" data-column="column1">Header 1</th>             <th class="column100 column2" data-column="column2">Header 2</th>           </tr>         </thead>         <tbody>           <tr class="row100">             <td class="wysiwyg-text-align-center">Line 1 Column 1</td>             <td class="wysiwyg-text-align-center">Line 1 Column 2</td>           </tr>           <tr class="row100">             <td class="column100 column1 wysiwyg-text-align-center"data-column="column1">Line 2 Column 1</td>             <td class="column100 column2 wysiwyg-text-align-center"data-column="column2">Line 2 Column 2</td>           </tr> <tr class="row100">             <td class="column100 column1 wysiwyg-text-align-center"data-column="column1">Line 3 Column 1</td>             <td class="column100 column2 wysiwyg-text-align-center"data-column="column2">Line 3 Column 2</td>           </tr>         </tbody>       </table>     </div>   </div> </div> ```  **Notes:** There can be as much columns and rows as you need.  Starting from second row add corresponding “column XX” number  Once html code is added you may resize table in Zendesk editor |
| **Internal text** | ``` <div class="internaldata">   <p>INTERNAL_TEXT  </p> </div> ``` |
