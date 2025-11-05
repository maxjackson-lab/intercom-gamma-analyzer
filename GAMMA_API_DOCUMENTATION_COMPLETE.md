# Gamma Generate API - Complete Documentation

**Source**: https://developers.gamma.app/docs  
**Scraped**: November 5, 2025  
**Pages Combined**: 6 documentation pages

---

# Table of Contents

1. [Introduction & Getting Started](#introduction--getting-started)
2. [Access and Pricing](#access-and-pricing)
3. [Get Help](#get-help)
4. [Generate API Parameters Explained](#generate-api-parameters-explained)
5. [List Themes and List Folders APIs](#list-themes-and-list-folders-apis)

---

# Introduction & Getting Started

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

# Access and Pricing

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

# Get Help

## Questions, quick feedback, and debugging

Join the [Gamma API Slack channel](https://join.slack.com/t/gambassadors/shared_invite/zt-39mcf05ys-419f~BVFyEtsCsDb9Ij3ow). For debugging help, include the x-request-id header from your API response.

## Broader feedback

You can use [this feedback form](https://docs.google.com/forms/d/e/1FAIpQLSeRHjChH8DS6YC4WS23LlOb1SC1Fw2HvuPFZ3HFM4rYj16oCg/viewform?usp=header) to provide broader feedback about the API.

## Contact support

If you need more help, you can [reach out to our Support team](https://help.gamma.app/en/articles/11016434-how-can-i-contact-gamma-support-or-provide-feedback).

---

# Generate API Parameters Explained

The sample API requests below shows all required and optional API parameters, as well as sample responses.

## Sample API Requests

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

# Top level parameters

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

**Example:**

```json
"inputText": "# The Final Frontier: Deep Sea Exploration\\n* Less than 20% of our oceans have been explored\\n* Deeper than 1,000 meters remains largely mysterious\\n* More people have been to space than to the deepest parts of our ocean\\n\\nhttps://img.genially.com/5b34eda40057f90f3a45b977/1b02d693-2456-4379-a56d-4bc5e14c6ae1.jpeg\\n---\\n# Technological Breakthroughs\\n* Advanced submersibles capable of withstanding extreme pressure\\n* ROVs (Remotely Operated Vehicles) with HD cameras and sampling tools\\n* Autonomous underwater vehicles for extended mapping missions\\n* Deep-sea communication networks enabling real-time data transmission\\n\\nhttps://images.encounteredu.com/excited-hare/production/uploads/subject-update-about-exploring-the-deep-hero.jpg?w=1200&h=630&q=82&auto=format&fit=crop&dm=1631569543&s=48f275c76c565fdaa5d4bd365246afd3\\n---\\n# Ecological Discoveries\\n* Unique ecosystems thriving without sunlight\\n* Hydrothermal vent communities using chemosynthesis\\n* Creatures with remarkable adaptations: bioluminescence, pressure resistance\\n* Thousands of new species discovered annually\\n---\\n# Scientific & Economic Value\\n* Understanding climate regulation and carbon sequestration\\n* Pharmaceutical potential from deep-sea organisms\\n* Mineral resources and rare earth elements\\n* Insights into extreme life that could exist on other planets\\n\\nhttps://publicinterestnetwork.org/wp-content/uploads/2023/11/Western-Pacific-Jarvis_PD_NOAA-OER.jpg\\n---\\n# Future Horizons\\n* Expansion of deep-sea protected areas\\n* Sustainable exploration balancing discovery and conservation\\n* Technological miniaturization enabling broader coverage\\n* Citizen science initiatives through shared deep-sea data"
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
- Here are some scenarios to guide your use of these parameters and explain how they work

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
- Works best when the instructions do not conflict with other parameters, eg, if the `textMode` is defined as `condense`, and the `additionalInstructions` say to preserve all text, the output will not be able to respect these conflicting requests.
- Character limits: 1-2000.

**Example:**

```json
"additionalInstructions": "Make the card headings humorous and catchy"
```

## `folderIds` _(optional)_

Defines which folder(s) your gamma is stored in.

- You can use the [GET Folders](https://developers.gamma.app/v1.0/update/docs/list-themes-and-folders-apis#/) endpoint to pull a list of folders. Or you can copy over the folderIds from the app directly.

![](https://files.readme.io/eefcb9b3f6404e96978f1a92aed2820c178ed1dbf550873c6e3da0538c466740-CleanShot_2025-11-03_at_14.27.362x.png)

- You must be a member of a folder to be able to add gammas to that folder.

**Example:**

```json
"folderIds": ["123abc456def", "456123abcdef"]
```

## `exportAs` _(optional)_

Indicates if you'd like to return the generated gamma as a PDF or PPTX file as well as a Gamma URL.

- Options are `pdf` or `pptx`
- Download the files once generated as the links will become invalid after a period of time.
- If you do not wish to directly export to a PDF or PPTX via the API, you may always do so later via the app.

**Example:**

```json
"exportAs": "pdf"
```

---

# textOptions

## `textOptions.amount` _(optional, defaults to `medium`)_

Influences how much text each card contains. Relevant only if `textMode` is set to `generate` or `condense`.

- You can choose between `brief`, `medium`, `detailed` or `extensive`

**Example:**

```json
"textOptions": {
    "amount": "detailed"
  }
```

## `textOptions.tone` _(optional)_

Defines the mood or voice of the output. Relevant only if `textMode` is set to `generate`.

- You can add one or multiple words to hone in on the mood/voice to convey.
- Character limits: 1-500.

**Example:**

```json
"textOptions": {
    "tone": "neutral"
  }
```

**Example:**

```json
"textOptions": {
    "tone": "professional, upbeat, inspiring"
  }
```

## `textOptions.audience` _(optional)_

Describes who will be reading/viewing the gamma, which allows Gamma to cater the output to the intended group. Relevant only if `textMode` is set to `generate`.

- You can add one or multiple words to hone in on the intended viewers/readers of the gamma.
- Character limits: 1-500.

**Example:**

```json
"textOptions": {
    "audience": "outdoors enthusiasts, adventure seekers"
  }
```

**Example:**

```json
"textOptions": {
    "audience": "seven year olds"
  }
```

## `textOptions.language` _(optional, defaults to `en`)_

Determines the language in which your gamma is generated, regardless of the language of the `inputText`.

- You can choose from the languages listed [here](https://developers.gamma.app/reference/output-language-accepted-values).

**Example:**

```json
"textOptions": {
    "language": "en"
  }
```

---

# imageOptions

## `imageOptions.source` _(optional, defaults to `aiGenerated`)_

Determines where the images for the gamma are sourced from. You can choose from the options below. If you are providing your own image URLs in `inputText` and want only those to be used, set `imageOptions.source` to `noImages` to indicate that Gamma should not generate additional images.

| Options for `source` | Notes |
| --- | --- |
| `aiGenerated` | If you choose this option, you can also specify the `imageOptions.model` you want to use as well as an `imageOptions.style`. These parameters do not apply to other `source` options. |
| `pictographic` | Pulls images from Pictographic. |
| `unsplash` | Gets images from Unsplash. |
| `giphy` | Gets GIFs from Giphy. |
| `webAllImages` | Pulls the most relevant images from the web, even if licensing is unknown. |
| `webFreeToUse` | Pulls images licensed for personal use. |
| `webFreeToUseCommercially` | Gets images licensed for commercial use, like a sales pitch. |
| `placeholder` | Creates a gamma with placeholders for which images can be manually added later. |
| `noImages` | Creates a gamma with no images. Select this option if you are providing your own image URLs in `inputText` and want only those in your gamma. |

**Example:**

```json
"imageOptions": {
    "source": "aiGenerated"
  }
```

## `imageOptions.model` _(optional)_

This field is relevant if the `imageOptions.source` chosen is `aiGenerated`. The `imageOptions.model` parameter determines which model is used to generate images.

- You can choose from the models listed [here](https://developers.gamma.app/reference/image-model-accepted-values).
- If no value is specified for this parameter, Gamma automatically selects a model for you.

**Example:**

```json
"imageOptions": {
	"model": "flux-1-pro"
  }
```

## `imageOptions.style` _(optional)_

This field is relevant if the `imageOptions.source` chosen is `aiGenerated`. The `imageOptions.style` parameter influences the artistic style of the images generated. While this is an optional field, we highly recommend adding some direction here to create images in a cohesive style.

- You can add one or multiple words to define the visual style of the images you want.
- Adding some direction -- even a simple one word like "photorealistic" -- can create visual consistency among the generated images.
- Character limits: 1-500.

**Example:**

```json
"imageOptions": {
	"style": "minimal, black and white, line art"
  }
```

---

# cardOptions

## `cardOptions.dimensions` _(optional)_

Determines the aspect ratio of the cards to be generated. Fluid cards expand with your content. Not applicable if `format` is `webpage`.

- Options if `format` is `presentation`: `fluid` **(default)**, `16x9`, `4x3`
- Options if `format` is `document`: `fluid` **(default)**, `pageless`, `letter`, `a4`
- Options if `format` is `social`: `1x1`, `4x5` **(default)** (good for Instagram posts and LinkedIn carousels), `9x16` (good for Instagram and TikTok stories)

**Example:**

```json
"cardOptions": {
  "dimensions": "16x9"
}
```

## `cardOptions.headerFooter` _(optional)_

Allows you to specify elements in the header and footer of the cards. Not applicable if `format` is `webpage`.

- Step 1: Pick which positions you want to populate. Options: `topLeft`, `topRight`, `topCenter`, `bottomLeft`, `bottomRight`, `bottomCenter`.
- Step 2: For each position, specify what type of content goes there. Options: `text`, `image`, and `cardNumber`.
- Step 3: Configure based on type.
  - For `text`, define a `value` (required)
  - For `image`:
    - Set the `source`. Options: `themeLogo` or `custom` image (required)
    - Set the `size`. Options: `sm`, `md`, `lg`, `xl` (optional)
    - For a `custom` image, define a `src` image URL (required)
  - For `cardNumber`, no additional configuration is available.
- Step 4: For any position, you can control whether it appears on the first or last card:
  - `hideFromFirstCard` (optional) - Set to `true` to hide from first card. Default: `false`
  - `hideFromLastCard` (optional) - Set to `true` to hide from last card. Default: `false`

**Example:**

```json
"cardOptions": {
    "headerFooter": {
      "topRight": {
        "type": "image",
        "source": "themeLogo",
        "size": "sm"
      },
      "bottomRight": {
        "type": "cardNumber",
      },
      "hideFromFirstCard": "true"
    },
}
```

**Example:**

```json
"cardOptions": {
    "headerFooter": {
      "topRight": {
        "type": "image",
        "source": "custom",
        "src": "https://example.com/logo.png",
        "size": "md"
      },
      "bottomRight": {
        "type": "text",
        "value": "© 2025 Company™"
      },
      "hideFromFirstCard": "true",
      "hideFromLastCard": "true"
    },
}
```

---

# sharingOptions

## `sharingOptions.workspaceAccess` _(optional, defaults to workspace share settings)_

Determines level of access members in your workspace will have to your generated gamma.

- Options are: `noAccess`, `view`, `comment`, `edit`, `fullAccess`
- `fullAccess` allows members from your workspace to view, comment, edit, and share with others.

**Example:**

```json
"sharingOptions": {
	"workspaceAccess": "comment"
}
```

## `sharingOptions.externalAccess` _(optional, defaults to workspace share settings)_

Determines level of access members **outside your workspace** will have to your generated gamma.

- Options are: `noAccess`, `view`, `comment`, or `edit`

**Example:**

```json
"sharingOptions": {
	"externalAccess": "noAccess"
}
```

## `sharingOptions.emailOptions` _(optional)_

### `sharingOptions.emailOptions.recipients` _(optional)_

Allows you to share your gamma with specific recipients via their email address.

**Example:**

```json
"sharingOptions": {
  "emailOptions": {
    "recipients": ["ceo@example.com", "cto@example.com"]
}
```

### `sharingOptions.emailOptions.access` _(optional)_

Determines level of access those specified in `sharingOptions.emailOptions.recipients` have to your generated gamma. Only workspace members can have `fullAccess`

- Options are: `view`, `comment`, `edit`, or `fullAccess`

**Example:**

```json
"sharingOptions": {
  "emailOptions": {
    "access": "comment"
}
```

---

# List Themes and List Folders APIs

List API methods support bulk fetching through cursor-based pagination. You can list folders with `GET /v1.0/folders` and list themes with `GET /v1.0/themes`. These endpoints share a common structure and accept the same pagination parameters.

## All list endpoints accept the following parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `query` | string (optional) | Search by name (case-insensitive). Filters results to items matching the search term. |
| `limit` | integer (optional) | Number of items to return per page. Maximum: 50. |
| `after` | string (optional) | Cursor token for fetching the next page. Use the nextCursor value from the previous response. |

## List response format

| Field | Type | Description |
| --- | --- | --- |
| `data` | array | Array of folder or theme objects. |
| `hasMore` | boolean | Indicates whether more pages exist. When true, use nextCursor to fetch the next page. |
| `nextCursor` | string or null | Opaque cursor token for the next page. Pass this value to the `after` parameter in your next request. Returns `null` on the last page. |

## List Themes

Returns a paginated list of the themes in the your workspace. This endpoint returns both workspace-specific and global themes in a single response, filterable via the `type` field.

### GET Themes

```curl
curl -X GET https://public-api.gamma.app/v1.0/themes \
-H "X-API-KEY: sk-gamma-xxxxxxxx"
```

### Themes response

Each theme object in the `data` array contains:

**Sample response:**

```json
{
  "id": "abcdefghi",
  "name": "Prism",
  "type": "custom",
  "colorKeywords": ["light","blue","pink","purple","pastel","gradient","vibrant"],
  "toneKeywords": ["playful","friendly","creative","inspirational","fun"]
}
```

The `type` field distinguishes between:

- `standard`: Global themes available to all workspaces
- `custom`: Workspace-specific themes

## List Folders

Returns a paginated list of the folders in your workspace.

### GET Folders

```curl
curl -X GET https://public-api.gamma.app/v1.0/folders \
-H "X-API-KEY: sk-gamma-xxxxxxxx"
```

### Folders response

Each folder object in the `data` array contains:

**Sample response:**

```json
{
  "id": "abc123def456",
  "name": "Business Proposals"
}
```

## Pagination Example: Fetch all folders

The example below is for fetching folders but also applies to listing themes.

### Get first page of folders

**Request 1:**

```
GET /v1.0/folders?limit=50
```

**Response 1:**

```json
{
  "data": [
    { "id": "abcdef", "name": "Design" },
    { "id": "xyzabc", "name": "Marketing" }
  ],
  "hasMore": true,
  "nextCursor": "abc123def456ghi789"
}
```

### Get additional folders

- The `after` parameter accepts a cursor string from a previous response to fetch the next page of results. Cursors are always forward-only—you cannot paginate backward through results.
- When `hasMore` is `false` and `nextCursor` is `null`, you've reached the end of the results.

**Request 2:**

```
GET /v1.0/folders?limit=50&after=abc123def456ghi789
```

**Response 2:**

```json
{
  "data": [
    { "id": "lmnop1", "name": "Sales" },
    { "id": "qrstuv", "name": "Product" }
  ],
  "hasMore": false,
  "nextCursor": "null"
}
```

## Query Example: Search for a theme

The example below shows how to search for a theme by name, and also applies to searching for folders.

### Search for themes with "dark" in the name

**Request:**

```
GET /v1.0/themes?query=dark&limit=50
```

**Response:**

```json
{
  "data": [
    {
      "id": "abc123def456",
      "name": "Standard Dark",
      "type": "standard",
      "colorKeywords": ["black", "gray", "accent"],
      "toneKeywords": ["sophisticated", "modern"]
    },
    {
      "id": "123abc456def",
      "name": "Dark Gradient",
      "type": "custom",
      "colorKeywords": ["purple", "black", "navy"],
      "toneKeywords": ["dramatic", "elegant"]
    }
  ],
  "hasMore": false,
  "nextCursor": "null"
}
```

The returned `id` can be used in the `themeId` parameter in the Generate and Create from Template APIs.

---

## Additional Resources

- **Slack Community**: [Join the Gamma API Slack channel](https://join.slack.com/t/gambassadors/shared_invite/zt-39mcf05ys-419f~BVFyEtsCsDb9Ij3ow)
- **Feedback Form**: [Provide broader feedback](https://docs.google.com/forms/d/e/1FAIpQLSeRHjChH8DS6YC4WS23LlOb1SC1Fw2HvuPFZ3HFM4rYj16oCg/viewform?usp=header)
- **Support**: [Contact Gamma Support](https://help.gamma.app/en/articles/11016434-how-can-i-contact-gamma-support-or-provide-feedback)
- **Help Center**: [How AI Credits Work](https://help.gamma.app/en/articles/7834324-how-do-ai-credits-work-in-gamma)
- **Pricing**: [View Pricing Plans](https://gamma.app/pricing)
- **About Gamma**: [Learn more](https://gamma.app/about)

---

**End of Documentation**

