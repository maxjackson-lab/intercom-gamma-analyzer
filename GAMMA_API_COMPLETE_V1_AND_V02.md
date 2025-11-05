# Gamma Generate API - Complete Documentation (v1.0 + v0.2 Legacy)

**Source**: https://developers.gamma.app  
**Scraped**: November 5, 2025  
**Current Version**: v1.0 (GA - Generally Available as of Nov 5, 2025)  
**Legacy Version**: v0.2 (Deprecated, will sunset January 16, 2026)

---

# ⚠️ IMPORTANT: API Version Information

## Current Version: v1.0 (Use This!)

- **Status**: Generally Available (GA)
- **Base URL**: `https://public-api.gamma.app/v1.0/`
- **Released**: November 5, 2025
- **Recommended**: Yes - all new integrations should use v1.0

## Legacy Version: v0.2 (Deprecated)

- **Status**: Deprecated
- **Base URL**: `https://public-api.gamma.app/v0.2/`
- **Sunset Date**: January 16, 2026
- **Action Required**: Migrate to v1.0 before Jan 16, 2026

## Key Differences Between v1.0 and v0.2

### New in v1.0:
- ✅ **Generate webpages** (new format option)
- ✅ **Headers and footers** customization
- ✅ **Input image URLs** directly in content
- ✅ **Define folders** for organization
- ✅ **Share via email** to specific recipients
- ✅ **Create from Template API** (beta) - Remix feature via API
- ✅ **List Themes API** - Programmatically fetch themes
- ✅ **List Folders API** - Programmatically fetch folders
- ✅ **No hard limits** on generations (subject to rate limits)
- ✅ Parameter name changes: `themeName` → `themeId`

### Removed Hard Limits:
- v0.2: 50 generations/day → v1.0: 50 generations/hour (soft limit)

---

# Table of Contents

## v1.0 Documentation (Current)
1. [v1.0 Introduction & Getting Started](#v10-introduction--getting-started)
2. [v1.0 Access and Pricing](#v10-access-and-pricing)
3. [v1.0 Generate API Parameters](#v10-generate-api-parameters-explained)
4. [v1.0 List Themes and Folders APIs](#v10-list-themes-and-list-folders-apis)
5. [v1.0 Error Codes](#v10-error-codes)

## v0.2 Documentation (Legacy)
6. [v0.2 Legacy API Reference](#v02-legacy-api-reference)
7. [v0.2 Legacy Endpoints](#v02-legacy-endpoints)

## Reference Data (Applies to Both Versions)
8. [Supported Languages](#supported-languages-both-versions)
9. [AI Image Models](#ai-image-models-both-versions)

---

# v1.0 Documentation (Current)

---

# v1.0 Introduction & Getting Started

> 🚧
>
> ### The Generate API is currently in beta
>
> - Gamma Pro and Ultra users get up to 50 generations/hour.
> - Functionality, rate limits, and pricing are subject to change.
> - During the beta, we may introduce breaking changes to the API with limited notice.

The Generate API allows you to programmatically create presentations, documents, and social media posts using Gamma. This API mirrors much of the AI generation functionality available through Gamma's web application.

![](https://files.readme.io/952dc4226d8f9cb0f57aff2f3fe9bb2bd1d9250910ad9efc01d362033ec9a037-CleanShot_2025-07-01_at_09.41.412x.jpg)

## What is Gamma?

[Gamma](https://gamma.app/about) is an AI-powered design partner that helps you create professional-looking presentations, documents, and social posts quickly using AI-generated content and images. The Gamma API extends this functionality to developers and users of automation tools, allowing them to integrate Gamma's content generation capabilities into their own applications and workflows.

## Key Features

**Versatile Content Creation**

Create presentations, documents, and social posts in various sizes and styles. Generate from any text -- a one-line prompt, messy notes, or polished content. Support for 60+ languages makes your content globally accessible.

**Intelligent Design**

Get thoughtfully designed content with customizable themes and images from AI or a source of your choosing. Fine-tune your output by defining tone, audience, and detail level.

**Seamless Workflow**

Further refine your API generated content in the Gamma app or export directly to PDF or PPTX via API. You can also connect Gamma into your favorite automation tool to create an end to end workflow.

## Ways to use the API

You can use the Gamma API in multiple ways:

- On automation platforms like Make, [Zapier](https://zapier.com/apps/gamma/integrations), Workato, N8N, etc, to automate your workflows
- By directly integrating it into backend code to power your apps

![](https://files.readme.io/97b4fc25ccdbc19261161c824d67bbf060755d1130cb2f20b398586ad7e35d52-CleanShot_2025-09-15_at_07.54.302x.png)

## Limitations

> 🚧
>
> ### The Generate API is currently in beta.
>
> **Functionality, rate limits, and pricing are subject to change.**

The beta version of the API has the following limitations:

- Rate limits: Maximum of 50 generations per hour per user.
- Authentication: We currently support authentication via API keys only, and OAuth is not yet supported.

---

# v1.0 Access and Pricing

## Access

- API access is available to subscribers on Pro, Ultra, Teams, and Business plans. View [pricing plans here](https://gamma.app/pricing).
- To get started, you can generate an API key through your account settings as shown below.

![](https://files.readme.io/2192df8ddd3190fe7d98eb06e2f5370d3a8300f2251bb0aa83a63790f3e35c6a-CleanShot_2025-07-28_at_12.43.382x.png)

## Usage and pricing

- API billing is conducted using a credit-based system, and higher tier subscribers receive more monthly credits.
- If you run out of credits, you can upgrade to a higher subscription tier, purchase credits ad hoc, or enable auto-recharge (_recommended_) at [https://gamma.app/settings/billing](https://gamma.app/settings/billing)

![](https://files.readme.io/7088518f8139672d05c42610c1e1a172e600d6f00ec2e6a16c5d0f45f7e46c7a-CleanShot_2025-10-01_at_07.40.082x.png)

## How credits work

Credit charges are determined based on several factors and are returned in the GET response.

| Feature | API parameter | Credits Charged* |
| --- | --- | --- |
| Number of cards | `numCards` | 3-4 credits/card |
| AI image model | `imageOptions.model` | - Basic models: ~2 credits/image<br>- Advanced models: ~10-20 credits/image<br>- Premium models: ~20-40 credits/image<br>- Ultra models: ~40-120 credits/image |

*Credit charges subject to change.

**Illustrative scenarios**

- Deck with 10 cards + 5 images generated using a basic image model = ~40-50 credits
- Doc with 20 cards + 15 images generated using a premium image model = ~360-680 credits
- Socials with 30 cards + 30 images generated using an ultra image model = ~1290-3720 credits

To learn more about credits, you can visit our [Help Center](https://help.gamma.app/en/articles/7834324-how-do-ai-credits-work-in-gamma).

---

# v1.0 Generate API Parameters Explained

The sample API requests below shows all required and optional API parameters, as well as sample responses.

## Sample API Requests (v1.0)

### Generate POST request

```curl
curl --request POST \
     --url https://public-api.gamma.app/v1.0/generations \
     --header 'Content-Type: application/json' \
     --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
     --data '
{
  "inputText": "Best hikes in the United States",
  "textMode": "generate",
  "format": "presentation",
  "themeId": "Oasis",
  "numCards": 10,
  "cardSplit": "auto",
  "additionalInstructions": "Make the titles catchy",
  "folderIds": ["123abc456", "456def789"],
  "exportAs": "pdf",
  "textOptions": {
    "amount": "detailed",
    "tone": "professional, inspiring",
    "audience": "outdoors enthusiasts, adventure seekers",
    "language": "en"
  },
  "imageOptions": {
    "source": "aiGenerated",
    "model": "imagen-4-pro",
    "style": "photorealistic"
  },
  "cardOptions": {
    "dimensions": "fluid",
    "headerFooter": {
      "topRight": {
        "type": "image",
        "source": "themeLogo",
        "size": "sm"
      },
      "bottomRight": {
        "type": "cardNumber"
      },
      "hideFromFirstCard": true,
      "hideFromLastCard": false
    }
  },
  "sharingOptions": {
    "workspaceAccess": "view",
    "externalAccess": "noAccess",
    "emailOptions": {
      "recipients": ["email@example.com"],
      "access": "comment"
    }
  },
}
'
```

### Success response

```json
{
  "generationId": "yyyyyyyyyy"
}
```

### Error response

```json
{
  "message": "Input validation errors: 1. …",
  "statusCode": 400
}
```

### Error: No credits

```json
{
  "message": "Forbidden",
  "statusCode": 403
}
```

### GET request

```curl
curl --request GET \
     --url https://public-api.gamma.app/v1.0/generations/yyyyyyyyyy \
     --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
     --header 'accept: application/json'
```

### Success: status pending

```json
{
  "status": "pending",
  "generationId": "XXXXXXXXXXX"
}
```

### Success: status completed

```json
{
  "generationId": "XXXXXXXXXXX",
  "status": "completed",
  "gammaUrl": "https://gamma.app/docs/yyyyyyyyyy",
  "credits":{"deducted":150,"remaining":3000}
}
```

### Error response

```json
{
  "message": "Generation ID not found. generationId: xxxxxx",
  "statusCode": 404,
  "credits":{"deducted":0,"remaining":3000}
}
```

---

# Top level parameters (v1.0)

## `inputText` _(required)_

Content used to generate your gamma, including text and image URLs.

**Add images to the input**

You can provide URLs for specific images you want to include. Simply insert the URLs into your content where you want each image to appear (see example below). You can also add instructions for how to display the images in `additionalInstructions`, eg, "Group the last 10 images into a gallery to showcase them together."

Note: If you want your gamma to use _only_ the images you provide (and not generate additional ones), set `imageOptions.source` to `noImages`.

**Token limits**

The token limit is 100,000, which is approximately 400,000 characters. However, in some cases, the token limit may be lower, especially if your use case requires extra reasoning from our AI models. We highly recommend keeping inputText below 100,000 tokens and testing out a variety of inputs to get a good sense of what works for your use case.

**Other tips**

- Text can be as little as a few words that describe the topic of the content you want to generate.
- You can also input longer text -- pages of messy notes or highly structured, detailed text.
- You can control where cards are split by adding \\n---\\n to the text.
- You may need to apply JSON escaping to your text. Find out more about JSON escaping and [try it out here](https://www.devtoolsdaily.com/json/escape/).

**Example:**

```json
"inputText": "Ways to use AI for productivity"
```

## `textMode` _(required)_

Determines how your `inputText` is modified, if at all.

- You can choose between `generate`, `condense`, or `preserve`
- `generate`: Using your `inputText` as a starting point, Gamma will rewrite and expand the content. Works best when you have brief text in the input that you want to elaborate on.
- `condense`: Gamma will summarize your `inputText` to fit the content length you want. Works best when you start with a large amount of text that you'd like to summarize.
- `preserve`: Gamma will retain the exact text in `inputText`, sometimes structuring it where it makes sense to do so, eg, adding headings to sections. (If you do not want any modifications at all, you can specify this in the `additionalInstructions` parameter.)

**Example:**

```json
"textMode": "generate"
```

## `format` _(optional, defaults to `presentation`)_

Determines the artifact Gamma will create for you.

- You can choose between `presentation`, `document`, `social`, or `webpage`.
- You can use the `cardOptions.dimensions` field to further specify the shape of your output.

**Example:**

```json
"format": "presentation"
```

## `themeId` _(optional, defaults to workspace default theme)_

Defines which theme from Gamma will be used for the output. Themes determine the look and feel of the gamma, including colors and fonts.

- You can use the [GET Themes](https://developers.gamma.app/v1.0/update/docs/list-themes-and-folders-apis#/) endpoint to pull a list of themes from your workspace. Or you can copy over the themeId from the app directly.

![](https://files.readme.io/d01171ca7562e427d8469ee2d0391e54400235ca558d6da8e61cf35e957d8833-CleanShot_2025-11-03_at_14.24.272x.png)

**Example:**

```json
"themeId": "abc123def456ghi"
```

## `numCards` _(optional, defaults to `10`)_

Determines how many cards are created if `auto` is chosen in `cardSplit`

- Pro users can choose any integer between 1 and 60.
- Ultra users can choose any integer between 1 and 75.

**Example:**

```json
"numCards": 10
```

## `cardSplit` _(optional, defaults to `auto`)_

Determines how your content will be divided into cards.

- You can choose between `auto` or `inputTextBreaks`
- Choosing `auto` tells Gamma to looks at the `numCards` field and divide up content accordingly. (It will not adhere to text breaks \\n---\\n in your `inputText`.)
- Choosing `inputTextBreaks` tells Gamma that it should look for text breaks \\n---\\n in your `inputText` and divide the content based on this. (It will not respect `numCards`.)
  - Note: One \\n---\\n = one break, ie, text with one break will produce two cards, two break will produce three cards, and so on.

| inputText contains \\n---\\n<br>and how many | cardSplit | numCards | output has |
| --- | --- | --- | --- |
| No | auto | 9 | 9 cards |
| No | auto | left blank | 10 cards (default) |
| No | inputTextBreaks | 9 | 1 card |
| Yes, 5 | auto | 9 | 9 cards |
| Yes, 5 | inputTextBreaks | 9 | 6 cards |

**Example:**

```json
"cardSplit": "auto"
```

## `additionalInstructions` _(optional)_

Helps you add more specifications about your desired output.

- You can add specifications to steer content, layouts, and other aspects of the output.
- Works best when the instructions do not conflict with other parameters.
- Character limits: 1-2000.

**Example:**

```json
"additionalInstructions": "Make the card headings humorous and catchy"
```

## `folderIds` _(optional)_

Defines which folder(s) your gamma is stored in.

- You can use the [GET Folders](https://developers.gamma.app/v1.0/update/docs/list-themes-and-folders-apis#/) endpoint to pull a list of folders. Or you can copy over the folderIds from the app directly.

![](https://files.readme.io/eefcb9b3f6404e96978f1a92aed2820c178ed1dbf550873c6e3da0538c466740-CleanShot_2025-11-03_at_14.27.362x.png)

**Example:**

```json
"folderIds": ["123abc456def", "456123abcdef"]
```

## `exportAs` _(optional)_

Indicates if you'd like to return the generated gamma as a PDF or PPTX file as well as a Gamma URL.

- Options are `pdf` or `pptx`
- Download the files once generated as the links will become invalid after a period of time.

**Example:**

```json
"exportAs": "pdf"
```

---

# textOptions (v1.0)

## `textOptions.amount` _(optional, defaults to `medium`)_

Influences how much text each card contains. Relevant only if `textMode` is set to `generate` or `condense`.

- You can choose between `brief`, `medium`, `detailed` or `extensive`

## `textOptions.tone` _(optional)_

Defines the mood or voice of the output. Relevant only if `textMode` is set to `generate`.

- Character limits: 1-500.

## `textOptions.audience` _(optional)_

Describes who will be reading/viewing the gamma. Relevant only if `textMode` is set to `generate`.

- Character limits: 1-500.

## `textOptions.language` _(optional, defaults to `en`)_

Determines the language in which your gamma is generated, regardless of the language of the `inputText`.

- See [Supported Languages](#supported-languages-both-versions) section below.

---

# imageOptions (v1.0)

## `imageOptions.source` _(optional, defaults to `aiGenerated`)_

Determines where the images for the gamma are sourced from.

| Options for `source` | Notes |
| --- | --- |
| `aiGenerated` | If you choose this option, you can also specify the `imageOptions.model` and `imageOptions.style`. |
| `pictographic` | Pulls images from Pictographic. |
| `unsplash` | Gets images from Unsplash. |
| `giphy` | Gets GIFs from Giphy. |
| `webAllImages` | Pulls the most relevant images from the web, even if licensing is unknown. |
| `webFreeToUse` | Pulls images licensed for personal use. |
| `webFreeToUseCommercially` | Gets images licensed for commercial use. |
| `placeholder` | Creates a gamma with placeholders for images. |
| `noImages` | Creates a gamma with no images. Select this if providing your own image URLs in `inputText`. |

## `imageOptions.model` _(optional)_

Relevant if `imageOptions.source` is `aiGenerated`. Determines which AI model generates images.

- See [AI Image Models](#ai-image-models-both-versions) section below.
- If not specified, Gamma automatically selects a model.

## `imageOptions.style` _(optional)_

Relevant if `imageOptions.source` is `aiGenerated`. Influences the artistic style of generated images.

- Character limits: 1-500.
- Highly recommended to add direction for visual consistency.

**Example:**

```json
"imageOptions": {
	"style": "minimal, black and white, line art"
}
```

---

# cardOptions (v1.0)

## `cardOptions.dimensions` _(optional)_

Determines the aspect ratio of the cards. Not applicable if `format` is `webpage`.

- **If `format` is `presentation`**: `fluid` (default), `16x9`, `4x3`
- **If `format` is `document`**: `fluid` (default), `pageless`, `letter`, `a4`
- **If `format` is `social`**: `1x1`, `4x5` (default), `9x16`

## `cardOptions.headerFooter` _(optional)_ **[NEW IN v1.0]**

Allows you to specify elements in the header and footer of cards. Not applicable if `format` is `webpage`.

**Positions**: `topLeft`, `topRight`, `topCenter`, `bottomLeft`, `bottomRight`, `bottomCenter`

**Types**: `text`, `image`, `cardNumber`

**Configuration**:
- For `text`: define `value` (required)
- For `image`: 
  - Set `source`: `themeLogo` or `custom` (required)
  - Set `size`: `sm`, `md`, `lg`, `xl` (optional)
  - For `custom`, define `src` URL (required)
- For `cardNumber`: no additional config

**Visibility controls**:
- `hideFromFirstCard` (optional, default: false)
- `hideFromLastCard` (optional, default: false)

---

# sharingOptions (v1.0)

## `sharingOptions.workspaceAccess` _(optional)_

Level of access for workspace members.

- Options: `noAccess`, `view`, `comment`, `edit`, `fullAccess`

## `sharingOptions.externalAccess` _(optional)_

Level of access for external users.

- Options: `noAccess`, `view`, `comment`, `edit`

## `sharingOptions.emailOptions` _(optional)_ **[NEW IN v1.0]**

Share with specific recipients via email.

### `recipients` _(optional)_

Array of email addresses.

### `access` _(optional)_

Access level for recipients: `view`, `comment`, `edit`, or `fullAccess`

---

# v1.0 List Themes and List Folders APIs

List API methods support bulk fetching through cursor-based pagination.

## Endpoints

- `GET /v1.0/folders` - List all folders
- `GET /v1.0/themes` - List all themes

## Common parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `query` | string (optional) | Search by name (case-insensitive) |
| `limit` | integer (optional) | Items per page. Maximum: 50 |
| `after` | string (optional) | Cursor token for next page |

## Response format

| Field | Type | Description |
| --- | --- | --- |
| `data` | array | Array of objects |
| `hasMore` | boolean | Indicates if more pages exist |
| `nextCursor` | string or null | Cursor for next page |

## List Themes Example

```curl
curl -X GET https://public-api.gamma.app/v1.0/themes \
-H "X-API-KEY: sk-gamma-xxxxxxxx"
```

**Response:**

```json
{
  "id": "abcdefghi",
  "name": "Prism",
  "type": "custom",
  "colorKeywords": ["light","blue","pink","purple"],
  "toneKeywords": ["playful","friendly","creative"]
}
```

The `type` field:
- `standard`: Global themes available to all workspaces
- `custom`: Workspace-specific themes

## List Folders Example

```curl
curl -X GET https://public-api.gamma.app/v1.0/folders \
-H "X-API-KEY: sk-gamma-xxxxxxxx"
```

**Response:**

```json
{
  "id": "abc123def456",
  "name": "Business Proposals"
}
```

## Pagination Example

**First page:**

```
GET /v1.0/folders?limit=50
```

**Next page:**

```
GET /v1.0/folders?limit=50&after=abc123def456ghi789
```

---

# v1.0 Error Codes

| Status Code | Message | Description |
| --- | --- | --- |
| 400 | Input validation errors | Invalid parameters. Check error details. |
| 401 | Invalid API key | API key is invalid or not associated with Pro account. |
| 403 | Forbidden | No credits left. Upgrade or refill credits. |
| 404 | Generation ID not found | Generation ID could not be located. |
| 422 | Failed to generate text | Generation produced empty output. Review inputs. |
| 429 | Too many requests | Rate limit exceeded. Retry after limit period. |
| 500 | An error occurred | Unexpected error. Contact support with x-request-id. |
| 502 | Bad gateway | Temporary gateway issue. Try again. |

---

# v0.2 Legacy API Reference

⚠️ **DEPRECATED - Will sunset January 16, 2026**

## v0.2 Endpoints

### POST - Generate a gamma

```curl
curl --request POST \
     --url https://public-api.gamma.app/v0.2/generations \
     --header 'Content-Type: application/json' \
     --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
     --data '
{
  "inputText": "Your content here",
  "textMode": "generate",
  "format": "presentation",
  "themeName": "Oasis",
  "numCards": 10
}
'
```

**Response:**

```json
{
  "generationId": "xxxxxxxxxxx"
}
```

### GET - Check generation status

```curl
curl --request GET \
     --url https://public-api.gamma.app/v0.2/generations/generationId \
     --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
     --header 'accept: application/json'
```

**Response when completed:**

```json
{
  "generationId": "XXXXXXXXXXX",
  "status": "completed",
  "gammaUrl": "https://gamma.app/docs/yyyyyyyyyy",
  "credits": {
    "deducted": 150,
    "remaining": 3000
  }
}
```

## v0.2 Legacy Parameters

### Key Differences from v1.0:

| v0.2 Parameter | v1.0 Parameter | Notes |
| --- | --- | --- |
| `themeName` | `themeId` | Changed to use IDs instead of names |
| N/A | `folderIds` | New in v1.0 - organize gammas |
| N/A | `cardOptions.headerFooter` | New in v1.0 - customize headers/footers |
| N/A | `sharingOptions.emailOptions` | New in v1.0 - share via email |
| N/A | `format: "webpage"` | New in v1.0 - create webpages |
| Character limit: 750,000 | Token limit: 100,000 (~400k chars) | Changed to token-based limit |
| `additionalInstructions`: 1-500 | `additionalInstructions`: 1-2000 | Increased character limit |

### v0.2 Parameters List

**Required:**
- `inputText` (string, 1-750,000 characters)
- `textMode` (string: generate, condense, preserve)

**Optional:**
- `format` (string: presentation, document, social) - Default: presentation
- `themeName` (string) - Default: workspace default
- `numCards` (integer: 1-60 for Pro, 1-75 for Ultra) - Default: 10
- `cardSplit` (string: auto, inputTextBreaks) - Default: auto
- `additionalInstructions` (string, 1-500 characters)
- `exportAs` (string: pdf, pptx)
- `textOptions` (object)
- `imageOptions` (object)
- `cardOptions` (object) - **Note**: No headerFooter support in v0.2
- `sharingOptions` (object) - **Note**: No emailOptions support in v0.2

---

# Supported Languages (Both Versions)

Use in `textOptions.language` parameter. Default: `en`

| Language | Key |
| --- | --- |
| Afrikaans | `af` |
| Albanian | `sq` |
| Arabic | `ar` |
| Arabic (Saudi Arabia) | `ar-sa` |
| Bengali | `bn` |
| Bosnian | `bs` |
| Bulgarian | `bg` |
| Catalan | `ca` |
| Croatian | `hr` |
| Czech | `cs` |
| Danish | `da` |
| Dutch | `nl` |
| English (India) | `en-in` |
| English (UK) | `en-gb` |
| English (US) | `en` |
| Estonian | `et` |
| Finnish | `fi` |
| French | `fr` |
| German | `de` |
| Greek | `el` |
| Gujarati | `gu` |
| Hausa | `ha` |
| Hebrew | `he` |
| Hindi | `hi` |
| Hungarian | `hu` |
| Icelandic | `is` |
| Indonesian | `id` |
| Italian | `it` |
| Japanese (です/ます style) | `ja` |
| Japanese (だ/である style) | `ja-da` |
| Kannada | `kn` |
| Kazakh | `kk` |
| Korean | `ko` |
| Latvian | `lv` |
| Lithuanian | `lt` |
| Macedonian | `mk` |
| Malay | `ms` |
| Malayalam | `ml` |
| Marathi | `mr` |
| Norwegian | `nb` |
| Persian | `fa` |
| Polish | `pl` |
| Portuguese (Brazil) | `pt-br` |
| Portuguese (Portugal) | `pt-pt` |
| Romanian | `ro` |
| Russian | `ru` |
| Serbian | `sr` |
| Simplified Chinese | `zh-cn` |
| Slovenian | `sl` |
| Spanish | `es` |
| Spanish (Latin America) | `es-419` |
| Spanish (Mexico) | `es-mx` |
| Spanish (Spain) | `es-es` |
| Swahili | `sw` |
| Swedish | `sv` |
| Tagalog | `tl` |
| Tamil | `ta` |
| Telugu | `te` |
| Thai | `th` |
| Traditional Chinese | `zh-tw` |
| Turkish | `tr` |
| Ukrainian | `uk` |
| Urdu | `ur` |
| Uzbek | `uz` |
| Vietnamese | `vi` |
| Welsh | `cy` |
| Yoruba | `yo` |

**Total**: 67 languages supported

---

# AI Image Models (Both Versions)

Use in `imageOptions.model` parameter when `imageOptions.source` is `aiGenerated`.

| Model Name | String | Credits/Image | Notes |
| --- | --- | --- | --- |
| **Basic Models (2 credits)** | | | |
| Flux Fast 1.1 | `flux-1-quick` | 2 | |
| Flux Kontext Fast | `flux-kontext-fast` | 2 | |
| Imagen 3 Fast | `imagen-3-flash` | 2 | |
| Luma Photon Flash | `luma-photon-flash-1` | 2 | |
| **Advanced Models (8-10 credits)** | | | |
| Flux Pro | `flux-1-pro` | 8 | |
| Imagen 3 | `imagen-3-pro` | 8 | |
| Ideogram 3 Turbo | `ideogram-v3-turbo` | 10 | |
| Luma Photon | `luma-photon-1` | 10 | |
| **Premium Models (15-20 credits)** | | | |
| Leonardo Phoenix | `leonardo-phoenix` | 15 | |
| Flux Kontext Pro | `flux-kontext-pro` | 20 | |
| Gemini 2.5 Flash | `gemini-2.5-flash-image` | 20 | |
| Ideogram 3 | `ideogram-v3` | 20 | |
| Imagen 4 | `imagen-4-pro` | 20 | |
| Recraft | `recraft-v3` | 20 | |
| **Ultra Models (30-120 credits)** | | | |
| GPT Image | `gpt-image-1-medium` | 30 | |
| Flux Ultra | `flux-1-ultra` | 30 | Ultra plan only |
| Imagen 4 Ultra | `imagen-4-ultra` | 30 | Ultra plan only |
| Dall E 3 | `dall-e-3` | 33 | |
| Flux Kontext Max | `flux-kontext-max` | 40 | Ultra plan only |
| Recraft Vector Illustration | `recraft-v3-svg` | 40 | |
| Ideogram 3.0 Quality | `ideogram-v3-quality` | 45 | Ultra plan only |
| GPT Image Detailed | `gpt-image-1-high` | 120 | Ultra plan only |

**Total**: 22 AI image models available

---

# Migration Guide: v0.2 → v1.0

## Breaking Changes

### 1. Parameter Name Changes

**Change `themeName` to `themeId`:**

```diff
- "themeName": "Oasis"
+ "themeId": "abc123def456"
```

**Action**: Use the List Themes API to get theme IDs, or copy from the app.

### 2. Base URL Change

```diff
- POST https://public-api.gamma.app/v0.2/generations
+ POST https://public-api.gamma.app/v1.0/generations
```

### 3. Input Character Limits

```diff
- Character limit: 750,000
+ Token limit: 100,000 (~400,000 characters)
```

**Action**: Most use cases unaffected. For very large inputs, consider chunking.

### 4. Additional Instructions Limit

```diff
- Character limits: 1-500
+ Character limits: 1-2000
```

## New Features to Adopt

### 1. Folder Organization

```json
{
  "folderIds": ["123abc456def", "456123abcdef"]
}
```

### 2. Headers and Footers

```json
{
  "cardOptions": {
    "headerFooter": {
      "topRight": {
        "type": "image",
        "source": "themeLogo",
        "size": "sm"
      },
      "bottomRight": {
        "type": "cardNumber"
      }
    }
  }
}
```

### 3. Email Sharing

```json
{
  "sharingOptions": {
    "emailOptions": {
      "recipients": ["email@example.com"],
      "access": "comment"
    }
  }
}
```

### 4. Webpage Format

```json
{
  "format": "webpage"
}
```

### 5. Image URLs in Input

Simply include image URLs directly in your `inputText`:

```
# My Presentation
https://example.com/image1.jpg
Some text here
https://example.com/image2.jpg
```

---

# Changelog

## November 5, 2025

**🎉 v1.0 Generally Available + v0.2 Deprecation Notice**

- ✅ Generate API moved from beta to GA
- ✅ Create from Template API launched (beta)
- ✅ New features: webpages, headers/footers, image URLs, folders, email sharing
- ✅ List Themes and List Folders APIs released
- ✅ Removed hard generation limits
- ✅ Official Make.com integration
- ⚠️ **v0.2 will be deprecated January 16, 2026**

## October 1, 2025

- Increased generation caps: 50/hour (from 50/day)
- Added credit purchase and auto-recharge options
- API generated gammas appear in separate dashboard tab

## September 15, 2025

- Increased usage caps to 50 generations/user/day
- New Ultra tier with more powerful image models
- Ultra users can generate up to 75-card gammas
- Introduced credits-based pricing system

## July 28, 2025

- Initial beta release of Generate API (v0.2)
- POST and GET endpoints launched

---

## Additional Resources

- **Slack Community**: [Join the Gamma API Slack channel](https://join.slack.com/t/gambassadors/shared_invite/zt-39mcf05ys-419f~BVFyEtsCsDb9Ij3ow)
- **Feedback Form**: [Provide feedback](https://docs.google.com/forms/d/e/1FAIpQLSeRHjChH8DS6YC4WS23LlOb1SC1Fw2HvuPFZ3HFM4rYj16oCg/viewform?usp=header)
- **Support**: [Contact Support](https://help.gamma.app/en/articles/11016434-how-can-i-contact-gamma-support-or-provide-feedback)
- **Help Center**: [How AI Credits Work](https://help.gamma.app/en/articles/7834324-how-do-ai-credits-work-in-gamma)
- **Pricing**: [View Plans](https://gamma.app/pricing)
- **About**: [Learn More](https://gamma.app/about)
- **Make Integration**: [Gamma on Make.com](https://www.make.com/en/integrations/gamma-app)
- **Zapier Integration**: [Gamma on Zapier](https://zapier.com/apps/gamma/integrations)

---

**End of Documentation**

