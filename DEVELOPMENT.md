# Frontend

Currently building using node version v18.20.4

## Prerequisites

Install the `pre-commit` tool and enable the hooks:

```bash
pip install pre-commit
pre-commit install
```

Check your changes with:

```bash
pre-commit run --files <changed files>
```

Ensure `custom_components/anycubic_cloud/frontend_panel/package.json` exists
before running any `npm` script.

Open a terminal inside the `custom_components/anycubic_cloud/frontend_panel` directory.

Run:
```bash
npm install
```

After installing dependencies, build the panel with:
```bash
npm run build
```

Build both the panel and the card using the command:
```bash
npm run build && npm run build_card
```

To build just the panel:
```bash
npm run build
```

To build just the card:
```bash
npm run build_card
```


# Translations

## Component

Edit source translation files in `custom_components/anycubic_cloud/translations/input_translation_files/`

Build output json files with:

```bash
python custom_components/anycubic_cloud/scripts/build_translations.py
```

All service strings are built from the `common` section.

## Frontend

Edit source translation files in `custom_components/anycubic_cloud/frontend_panel/localize/languages`

Add new languages to `custom_components/anycubic_cloud/frontend_panel/localize/localize.ts` following the below edits, using German as an example:


```ts
import * as en from './languages/en.json';
import * as de from './languages/de.json';
````

```ts
var languages: any = {
  en: en,
  de: de,
};
````

Rebuild the frontend.
