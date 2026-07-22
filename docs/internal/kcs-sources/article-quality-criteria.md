# KCS Article Quality Criteria

Status: reviewable Markdown snapshot; the canonical Confluence page is the
source of truth.

- Canonical source:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/5422743564/KCS+Article+Quality+Criteria>
- Related examples locator:
  <https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902730/Article+Quality+criteria#Examples>
- Source role: normative article-quality acceptance criteria.
- Captured: 2026-07-22 from the operator-provided Confluence export.
- Export filename: `Article+Quality+criteria (1).doc` (not tracked).
- Export SHA-256:
  `9955dfdec1727d6747a98df24f8f9b0f39718f652fb07b86ece14c28424f1bf6`.

The attached image reference is intentionally omitted. The separate
best-practices example-pack snapshot records the slide evidence. When this
snapshot and the canonical page differ, use the canonical page and refresh the
snapshot before changing runtime behavior.

- [Introduction](#ArticleQualitycriteria-Introduction)
- [Publishing Legitimacy](#ArticleQualitycriteria-PublishingLegitimacy)
  - [Solution Provided](#ArticleQualitycriteria-SolutionProvided)
  - [Article is actual](#ArticleQualitycriteria-Articleisactual)
  - [Knowledge matches Product Context](#ArticleQualitycriteria-KnowledgematchesProductContext)
- [Easy-to-Use](#ArticleQualitycriteria-Easy-to-Use)
  - [KB is easy to understand/apply](#ArticleQualitycriteria-KBiseasytounderstand/apply)
  - [There are no additional branches in resolution](#ArticleQualitycriteria-Therearenoadditionalbranchesinresolution)
  - [Screenshots / video are added to the solution (if necessary)](#ArticleQualitycriteria-Screenshots/videoareaddedtothesolution(ifnecessary))
  - [GUI solution is presented (if exists)](#ArticleQualitycriteria-GUIsolutionispresented(ifexists))
  - [Scripting opportunity / Source Control](#ArticleQualitycriteria-Scriptingopportunity/SourceControl)
  - [Language is easy](#ArticleQualitycriteria-Languageiseasy)
- [Layout](#ArticleQualitycriteria-Layout)
  - [The title is not generalized](#ArticleQualitycriteria-Thetitleisnotgeneralized)
  - [Hub structure is avoided](#ArticleQualitycriteria-Hubstructureisavoided)
  - [Structure corresponds to the article type](#ArticleQualitycriteria-Structurecorrespondstothearticletype)
  - [Symptoms are as they're seen by customer](#ArticleQualitycriteria-Symptomsareasthey'reseenbycustomer)
  - [Style Guide is properly followed](#ArticleQualitycriteria-StyleGuideisproperlyfollowed)
  - [Tagging is proper](#ArticleQualitycriteria-Taggingisproper)
- [Examples](#ArticleQualitycriteria-Examples)

# Introduction

This page describes the Article Quality criteria set and helps to understand the basic principles and best practicies of making a good article.

# Publishing Legitimacy

## Solution Provided

Every public KB should have resolution/workaround/ETA for fix (in case of some Security Announcements). Other articles should be internal.

## Article is actual

If you see the public article that has obsolete knowledge – make it internal.

## Knowledge matches Product Context

Each case encountered should be published in KCS if the knowledge in this case matches the context of product usage. Generic knowledge is better to be referred to external resources (official resources like Google, Amazon, CentOS, Red Hat, MS, etc.), the link should be to the solution precisely.

# Easy-to-Use

## KB is easy to understand/apply

The resolution path should be easy so the customer could apply the solution without any complications – for the Symptom there should be correct Cause and corresponding Resolution.

## There are no additional branches in resolution

The resolution path should be logical (straightforward) without confusing branches (no if-else conditions)

## Screenshots / video are added to the solution (if necessary)

Using additional helpers like screenshots/videos is a plus, they should match the resolution context

## GUI solution is presented (if exists)

Whatever is possible to be done through panel/GUI is to be used as primary solution. CLI wise solutions may follow under spoiler in advanced section.

## Scripting opportunity / Source Control

If KB contains many shell commands that should be executed without human involvement – make a shell script and attach it to the article. If the efforts to run script demand the same as running the commands – there is no need to write scripts.

**Note:** Every script should not be uploaded as an attachment to the article, but should relay in the [**github repository**](https://github.com/plesk/kb-scripts) in order to keep the script maintained by the engineering team. Link to the script will look like:

# wget https://raw.githubusercontent.com/plesk/kb-scripts/master/<article\_number>/<name\_of\_the\_script>

All the needed information about Version Control you can find in the [**following guide**](https://webpros.atlassian.net/wiki/spaces/CX/pages/3470459988/Scripting+requirements+for+the+public+KB+articles).

## Language is easy

Watch your grammar and use easy-readable structures. Avoid:

- misspelling;
- passive voice;
- complex grammatical structure;

**Note:**even if the sentence is grammatically correct, it might be hard to understand and interpret for non-native speakers.

# Layout

## The title is not generalized

Title of the article should not be too general. For example, “Plesk does not work” is not a proper title and should be reworked to be more specific. Adding the error message might help. Also ensure the title won’t attract an unrelated audience. E.g. “MySQL is down” without mentioning Plesk will attract an audience who don’t use Plesk. That’s what we’d like to avoid.

## Hub structure is avoided

Additional section should not be overfilled with the cross-links to the articles that do not correspond to the case at all.

**To avoid bad crosslinking, justify the necessity of the link:**

1.Get the context (I did this and saw 500 error)

2.Define the obvious case and solution.

3.Consider: **HUBs are evil**

## Structure corresponds to the article type

Each article should have the common structure and default formatting for the appropriate type

## Symptoms are as they're seen by customer

Symptoms part should be precise and outline the issue as it is seen by the customer. And it should be a unique one. In the symptom part there should be no internals that can be found during the troubleshooting if they are excessive.

## Style Guide is properly followed

Common items/formatting, list hierarchy and separators are proper, using spoilers when applicable, etc.

## Tagging is proper

Use Proper TAGs which are tied to proper OS and Plesk version. If there are several versions in the resolution – tag might be generalized

# Examples

To see the examples for each practice - please refer to the Slide Deck attached

[Source image omitted from Markdown snapshot.]
