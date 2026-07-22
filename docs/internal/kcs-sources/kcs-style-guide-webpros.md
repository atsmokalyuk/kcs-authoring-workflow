# WebPros KCS Style Guide

Status: reviewable Markdown snapshot; the canonical Confluence page is the
source of truth.

- Canonical source:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902448/KCS+Style+Guide>
- Source role: broader cross-brand normative guide and cross-check source.
- Captured: 2026-07-22 from the operator-provided Confluence export.
- Export filename: `The+KCS+Style+Guide.doc` (not tracked).
- Export SHA-256:
  `5a7f03e288a6f0699bdb6d0429f614629f9c94aa2247fd2df04447bbcf0acc6a`.

Plesk-specific rules take precedence for Plesk article behavior. Confluence
images are intentionally omitted from this text snapshot. When the snapshot
and canonical page differ, use the canonical page and refresh this file before
changing runtime behavior.

- [What Is “The KCS Style Guide?”](#TheKCSStyleGuide-WhatIs“TheKCSStyleGuide?”)
- [Article Structure Requirements](#TheKCSStyleGuide-ArticleStructureRequirements)
  - [Article Title (Subject)](#TheKCSStyleGuide-ArticleTitle(Subject))
  - [Article environment labels](#TheKCSStyleGuide-Articleenvironmentlabels)
  - [Article body](#TheKCSStyleGuide-Articlebody)
  - [Article labels](#TheKCSStyleGuide-Articlelabels)
- [Attaching Files And Screenshots](#TheKCSStyleGuide-AttachingFilesAndScreenshots)
  - [Screenshot Capturing And Formatting](#TheKCSStyleGuide-ScreenshotCapturingAndFormatting)
  - [Drag And Drop](#TheKCSStyleGuide-DragAndDrop)
  - [Manual](#TheKCSStyleGuide-Manual)
- [Content formatting](#TheKCSStyleGuide-Contentformatting)

# What Is “The KCS Style Guide?”

This guide covers the rules to help make an article unified, readable, simple & easy to understand, and apply.

# Article Structure Requirements

Every article has the following items:

- Title
- Environment
- Body
- Labels

Each item of the article structure has its own requirements.

## Article Title (Subject)

An article’s title should contain all the required information to help the customer understand if the article is helpful.

[Source image omitted from Markdown snapshot.]

For example, a customer opens a ticket stating they are unable to export a database due to a permission denied error.

> Unable to export database. Error message:
>
> -- Connecting to localhost...
> mariadb-dump: Got error: 1044: "Access denied for user 'USERNAME'@'localhost' to database 'DB\_NAME'" when using LOCK TABLES due to a hostname error.

The article title should look like:

> Database export fails: Access denied for user 'jdoe'@'localhost' to database 'example\_db' when using LOCK TABLES

[Source image omitted from Markdown snapshot.]

A How To/Question & Answer article needs to have a short clear question on what is being asked or accomplished.

A How To example:

> How to disable recursive DNS queries?

A Question & Answer example:

> Does Plesk support PHP 5.4?

## Article environment labels

Article environment is represented by “*Applicable to*” section of the article. This section is generated and styled automatically based on “*Environmental labels*.”

Plesk - Please note! The platform is mandatory, all the articles without a platform will be removed.

[Source image omitted from Markdown snapshot.]

Such labels should contain the ticket’s environment and a platform like the following:

| **For Plesk** |
| --- |
| Plesk for Windows |
| Plesk for Linux |
| Plesk Obsidian for Windows |
| Plesk Obsidian for Linux |
| Plesk Onyx 17.8 for Windows |
| Plesk Onyx 17.8 for Linux |
| plesk env label.png |
| plesk app to.png |

## Article body

The article body contains the main content of the article: the issue or question description, cause (if any), and the resolution or answer.

To make the article easy to understand, it must contain the below corresponding sections for the article type.

Technical articles with errors cannot be ‘How to’ articles and should contain **Symptoms/Cause/Resolution** structure.

If it is required to use a “*How To*” or “*Question & Answer*” article in a technical article, it may be linked in the “*Resolution*” section.

[Source image omitted from Markdown snapshot.]

These articles have 3 sections:

- **Symptoms** – All errors, behaviors, and situations provided by the customer or found during an investigation are described in the “*Symptoms*” section. In general, symptoms help to determine if the article is suitable for the issue experienced. The “*Symptoms*” section uses the customer’s words with small cosmetic corrections and our findings during the investigation. The importance of using the customer’s words is help other customer’s locate the article, even if technically incorrect.
- **Cause** – The explanation of the root reason why the “*Symptoms*” happen are explained in the “*Cause*” section. Not all articles will have a “*Cause*.”
- **Resolution** – Any workarounds or steps to fix the reported issue is provided in the “*Resolution*” section. The resolution should be the steps used as the reply to the ticket with steps on how to fix the issue.

Please note, any explanations why the reported issue happens should be included in the “*Cause*” section.

[Source image omitted from Markdown snapshot.]

[Source image omitted from Markdown snapshot.]

These articles have 2 sections:

- **Question** – Any behavior that is described with a question (generically) or how to do something is explained in the “*Question*” section.
- **Answer** – The answer or steps on how to do something is listed in the “*Answer*” section.

[Source image omitted from Markdown snapshot.]

## Article labels

Labels are important because they help to:

- find the required article faster
- identify the version or platform for the customer
- notice support drivers and transfer it to R&D (Plesk: Research and Development, cPanel: Product Development/QA) for improvements

[Source image omitted from Markdown snapshot.]

Every article must contain one of the below labels used to identify the type of article:

The last 2 labels are to be used by engineers, all others should not be touched as they are added automatically.

1. If there is no special labels in the article, add either*“***kb: how-to**”or*“***kb: technical**.”
2. If you noticed an article with the incorrect label of *“***kb: how-to**”or *“***kb: technical**” - fix it.
3. In case “**kb: bug**,” “**kb: fixed**,” “**kb: tools**” or “**kb: auxiliary**” label is already added, *do not change/add special tags.*

- **kb: bug** - Articles about product bug cases that have not been fixed yet. This label is set automatically by the script when a Jira case ID is mentioned in the article. The script replaces the labels “**kb: technical**” or “**kb: how-to***.*”
- **kb: fixed** - Articles about product bug cases that were mentioned in the Release Notes as fixed:

  - cPanel: <https://docs.cpanel.net/changelogs/>
  - Plesk: <https://docs.plesk.com/release-notes/obsidian/change-log/>
- **kb: tools**- Articles that describe processes or how to use a utility. “Tools” articles are often used as a separate step in other articles.
- **kb: auxiliary** - General articles that are used as a part of the solution.

  - For example, the customer reports that an extension does not work. The article used recommends reinstalling the extension and references <https://support.plesk.com/hc/en-us/articles/12377511962007-How-to-manage-Plesk-extensions-install-disable-remove-update> as one of the steps. This article does not have any symptoms, it describes the process that helps to fix the initial customer's issue. In this case, <https://support.plesk.com/hc/en-us/articles/12377511962007-How-to-manage-Plesk-extensions-install-disable-remove-update> is an auxiliary article.
- **kb: how-to** - Technical question/answer articles that provide instructions for the particular customer's question. Added automatically when the "**Question & Answer**" article template is used.
- **kb: technical** - All Problem/Solutions articles. Added automatically for new articles when the "**Problem**" article template is used.
- **kb: security** - All Security case (CVE) articles. Added automatically for new articles when the "**CVE**" article template is used.

[Source image omitted from Markdown snapshot.]

Labels with technical tags listed below should not be touched:

- **FR:\*\*\***
- **DoNotDelete:docref**
- **MT and MG**

[Source image omitted from Markdown snapshot.]

These labels should be added manually to the corresponding article as needed for extensions.

All labels start with “**ext:** ” for example (but not limited to):

- **ext: wptk**
- **ext: migrator**
- **ext: acronis**
- **ext: kolab**
- **ext: pes**

# Attaching Files And Screenshots

Always attach files in the following formats:

- Linux - **.tar.gz**
- Windows - **.zip**

- Always sanitize any screenshots of sensitive data.
- If the article is published, verify the image is seen in incognito mode while not signed in.

There are two methods to add an image or file to an article:

- Drag-and-drop
- Manual

## Screenshot Capturing And Formatting

All highlighted elements, boxes and arrows, needs to be in the color red.

[Source image omitted from Markdown snapshot.]

To take a screenshot on a MAC, please follow the instructions at <https://support.apple.com/en-us/102646>. MAC saves screenshots as .png by default.

To highlight elements in an image on MAC, please follow the instructions at <https://discussions.apple.com/docs/DOC-8881>.

[Source image omitted from Markdown snapshot.]

To take a screenshot on Windows, please follow the instructions at <https://support.microsoft.com/en-us/windows/use-snipping-tool-to-capture-screenshots-00246869-1843-655f-f220-97299b865f6b>. After screenshot creation, save it as a **.png** file.

To highlight elements in an image on Windows, please see <https://www.microsoft.com/en-US/windows/paint#backgroundremoval> for more information.

## Drag And Drop

[Source image omitted from Markdown snapshot.]

Images or screenshots to visually assist the customer should go in the body (the left section).

[Source image omitted from Markdown snapshot.]

The image will upload and display where it was dropped.

[Source image omitted from Markdown snapshot.]

[Source image omitted from Markdown snapshot.]

Files that contain scripts or configurations should go in the files section (to the right).

[Source image omitted from Markdown snapshot.]

A new window to manage the uploaded media will appear and the file that was dropped will be preselected.

[Source image omitted from Markdown snapshot.]

Once the file is selected, Click “**Attach media**.”

[Source image omitted from Markdown snapshot.]

## Manual

[Source image omitted from Markdown snapshot.]

1. In “**Article Settings**” under “**Attached media**,” click on “**Manage attached media**.”

   [Source image omitted from Markdown snapshot.]
2. In upper right corner of the window that appears, click on “**Upload media**.”

   [Source image omitted from Markdown snapshot.]
3. The file selector window will open, select the desired image or file and click “**Open**.”

   [Source image omitted from Markdown snapshot.]
4. The media will be preselected in the Media Library.

   [Source image omitted from Markdown snapshot.]
5. Click “**Attach media**.”

   [Source image omitted from Markdown snapshot.]

# Content formatting

Text formatting is used to make an article appealing and easy to read.

|  |  |
| --- | --- |
| **Paths** | Path in any GUI (cPanel, Linux, Plesk, WHM, Windows, etc.) must be **bold**. For example:  cPanel: **Home / DNS Functions / Add a DNS Zone**  Plesk: **Tools & Settings > Server Components > DNS Server** |
| **Buttons and menus** | Name of any button or menu must be **bold**. For example:  **Save** |
| **Inline command-line utility names, paths** | Inline command-line utility names, paths to any log files/directories, or inline commands output should be printed with typescript by using <code></code> tag. For example:  cPanel: `/scripts/restartsrv_httpd`, `/var/cpanel/userdata/username/domain`  Plesk: `vhostmng.exe`, `/usr/local/psa/bin/admin` |
| **Product names** | Do not highlight product names in any way. They should be in plain text. For example (but not limited to):   - Apache - cPanel - Comodo - Plesk |
| **Windows paths** | When specifying Windows paths, always use `%plesk_dir%`, `%plesk_bin%`, `%plesk_cli%`, `%plesk_vhosts%` and `%windir%` where applicable instead of full paths.  Exception: paths in errors |
| Zendesk KCS editor supports triggers. Triggers automate article formatting and can be used without editing article’s source code.  It is mandatary to use them when formatting shell output, error messages, etc.  For more information and visual examples, please see:   - Comet Backup: COMING SOON - cPanel: [KCS: Style triggers](https://support.cpanel.net/hc/en-us/articles/35770927506327-KCS-Style-Triggers) - Plesk: [KCS: Style triggers](https://support.plesk.com/hc/en-us/articles/12378148057495-KCS-Style-triggers) - WebPros: [KCS Style triggers](https://support.webpros.com/hc/en-us/articles/37027850535447-Help-Center-Style-Triggers)   Please note! There must be a space between the trigger and the text. | |
| **Windows Command Prompt** | **Usage:**  `C:\> text here`  **Result:** |
| **Windows PowerShell** | **Usage:**  `PS text here`  **Result:** |
| **Linux shell** | **Usage:**  `# text here`  **Result:** |
| **MySQL queries on Windows** | **Usage:**  `MYSQL_WIN: text here`  **Result:** |
| **MySQL queries on Linux** | **Usage:**  `MYSQL_LIN: text here`  **Result:** |
| **Notes** | **Usage:**  `Note: text here`  **Result:** |
| **Warnings** | **Usage:**  `Warning: text here`  **Result:** |
| **Plesk UI errors** that have a **pink** background (mail errors, update errors and etc) | **Usage:**  `PLESK_ERROR: text here`  **Result:** |
| **cPanel & WHM UI errors** that have a **red** background (mail errors, update errors and etc) | **Usage:**  `CPANEL_ERROR: text here`  **Result:** |
| **Plesk UI warnings** that have yellow background. | **Usage:**  `PLESK_WARN: text here`  **Result:** |
| **cPanel UI warnings** that have yellow background. | **Usage:**  `CPANEL_WARN: text here`  **Result:** |
| **Plesk errors and messages** that have **white/gray** background in Plesk(MySQL access denied errors and etc) | **Usage:**  `PLESK_INFO: text here`  **Result:** |
| **cPanel UI errors and messages** that have **blue** background. | **Usage:**  `CPANEL_INFO: text here`  **Result:** |
| **Configuration directives and content of logs/config files** | **Usage:**  `CONFIG_TEXT: text here`  **Result:** |
| For finer tuning of an article, the source code can be edited. Articles use standard HTML markdown and can be opened in the KCS editor.  For example, <p></p> tags for paragraphs, <ol></ol> for ordered lists, etc. | |
| **Clickable image preview** | Images that require being maximized should have class '**resizable**' assigned in the following way: image-20250314-074136.png There is no need to specify the width and height inside the <img> tag with aforementioned class. By default the image will have width=460, hovering on them will return the hint 'Click to maximize'. On clicking the image the lightbox with the bigger picture will appear. It can be closed either clicking the cross in the upper right corner, or anywhere on the display.  Aforementioned behavior could be observed in the [following article](https://support.plesk.com/hc/en-us/articles/12377676289815). |
| **Text spoiler (expand)** | ``` <div class="accordion__item">     <div class="accordion__item-title">       <strong>Accordion item</strong>     </div>     <div class="accordion__item-content">       <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>     </div> </div> ``` |
| **Tabs** | ``` <div class="tabs-content">     <div id="1" class="tab-header current">Header of the Tab1</div>     <div id="content1" class="tab-content active">         Content of the Tab 1     </div>     <div id="2" class="tab-header">Header of the Tab2</div>     <div id="content2" class="tab-content">         Content of the Tab 2     </div>     <div id="3" class="tab-header">Header of the Tab3</div>     <div id="content3" class="tab-content">         Content of the Tab 3     </div> </div> ```  **Notes:**   1. There can be as many segments as you need, it is not limited to 2 or 3 tabs only 2. The first (default) tab should be defined like this (note: there should be **only one** default tab):   ``` <div id="1" class="tab-header current">Header of the Tab1</div> <div id="content1" class="tab-content active">         Content of the Tab 1 </div> ```   3. All subsequent tabs can be defined like this:   ``` <div id="<ID>" class="tab-header">Header of the Tab</div> <div id="content<ID>" class="tab-content">         Content of the Tab  </div> ```  **Important:** make sure to replace `id="ID"` and `id="content<ID>"` values with the actual tab’s number, for example:  ``` <div id="2" class="tab-header">Tab number 2</div> <div id="content2" class="tab-content">         Tab number 2's content </div> ```   4. All segments should be wrapped with a single `<div class="tabs-contents"> </div>` 5. As tab’s headers should be as short as possible, it’s recommended to add some heading with `<h3></h3>` |
| **Tables** | ``` <div class="tabs-content"> <div class="container-table100">   <div class="wrap-table100">     <div class="table100 ver1">       <table data-vertable="ver1">         <thead>           <tr class="row100 head">             <th class="column100 column1" data-column="column1">Header 1</th>             <th class="column100 column2" data-column="column2">Header 2</th>           </tr>         </thead>         <tbody>           <tr class="row100">             <td class="wysiwyg-text-align-center">Line 1 Column 1</td>             <td class="wysiwyg-text-align-center">Line 1 Column 2</td>           </tr>           <tr class="row100">             <td class="column100 column1 wysiwyg-text-align-center"data-column="column1">Line 2 Column 1</td>             <td class="column100 column2 wysiwyg-text-align-center"data-column="column2">Line 2 Column 2</td>           </tr> <tr class="row100">             <td class="column100 column1 wysiwyg-text-align-center"data-column="column1">Line 3 Column 1</td>             <td class="column100 column2 wysiwyg-text-align-center"data-column="column2">Line 3 Column 2</td>           </tr>         </tbody>       </table>     </div>   </div> </div> ```  **Notes:** There can be as much columns and rows as you need.  Starting from second row add corresponding “column XX” number  Once html code is added you may resize table in Zendesk editor |
| **Internal text** | ``` <div class="internaldata">   <p>INTERNAL_TEXT  </p> </div> ``` |
