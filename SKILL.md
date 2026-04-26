---
name: screenshot-studio-toolkit
description: Self-contained AI image production toolkit for agent-generated app store screenshots and marketing images. Use when Codex or another agent needs to generate App Store screenshots, marketing images, portrait/commercial templates, Grsai Banana or GPT Image2 images, reference-image generations, 1K/2K/4K outputs, batch grids, or local resize/crop/split exports without opening a React app.
---

# Screenshot Studio Toolkit

## Purpose

Use this skill as a self-contained image production toolchain. It can run without opening the original React app or starting `localhost:3000`.

The primary executable is:

```bash
scripts/studio_generate.py
```

The core workflow is:

1. Choose a scene mode and target format.
2. Choose provider/model and resolve model-specific capability limits.
3. Build a production prompt with hidden layout guardrails.
4. Generate one provider image, optionally as a multi-cell grid.
5. Resize, crop, or split locally into final deliverables.
6. Verify output count, dimensions, and UI availability.

## Quick Generate

Set a Grsai API key:

```bash
export GRSAI_API_KEY="..."
```

Optional custom provider base URLs:

```bash
export GRSAI_BASE_URL="https://your-provider.example"
export GRSAI_DRAW_URL="https://your-provider.example/v1/draw/nano-banana"
export GRSAI_GPT_IMAGE2_DRAW_URL="https://your-provider.example/v1/draw/completions"
export GRSAI_RESULT_URL="https://your-provider.example/v1/draw/result"
```

Preview a Banana batch request without network calls:

```bash
python3 scripts/studio_generate.py \
  --prompt "亚洲拉拉队球场热舞" \
  --model nano-banana \
  --mode general \
  --ratio "1:1" \
  --size 2K \
  --grid 2x3 \
  --count 6 \
  --dry-run
```

Generate and split a Banana batch:

```bash
python3 scripts/studio_generate.py \
  --prompt "亚洲拉拉队球场热舞" \
  --model nano-banana \
  --mode general \
  --ratio "1:1" \
  --size 2K \
  --grid 2x3 \
  --count 6 \
  --out ./outputs \
  --prefix cheer
```

Generate with GPT Image2:

```bash
python3 scripts/studio_generate.py \
  --prompt "美女写真" \
  --model gpt-image-2 \
  --mode general \
  --ratio "1:1" \
  --size 2K \
  --out ./outputs \
  --prefix portrait
```

Generate an App Store screenshot:

```bash
python3 scripts/studio_generate.py \
  --prompt "生成带状态栏的iPhone上架图，体现家长管理孩子玩pad的无奈" \
  --model nano-banana \
  --mode appstore \
  --device iphone_6_5_inch \
  --size 4K \
  --out ./outputs \
  --prefix appstore
```

Add reference images by repeating `--reference` with URLs, data URLs, or local file paths.

Use a custom provider URL directly:

```bash
python3 scripts/studio_generate.py \
  --prompt "美女写真" \
  --model gpt-image-2 \
  --mode general \
  --ratio "1:1" \
  --size 2K \
  --api-key "$CUSTOM_PROVIDER_KEY" \
  --base-url "https://your-provider.example" \
  --out ./outputs
```

## Executable Script

`scripts/studio_generate.py` is independent from the original web app. It implements:

- Grsai Banana request building, submission, polling, and download.
- GPT Image2 `/v1/draw/completions` request building with `size:auto`.
- Scene presets for AppStore, general ratios, marketing, portrait, and commercial outputs.
- 1K/2K/4K target sizing and Banana 4K canvas snapping.
- Batch-grid prompt generation.
- Output grid validation.
- Local Pillow-based cover-resize and grid splitting.
- JSON result output for agent consumption.

Useful flags:

- `--dry-run`: print the plan and exact request body; do not call the network.
- `--model`: `nano-banana`, `nano-banana-pro`, `nano-banana-2`, `gpt-image-2`, etc.
- `--mode`: `appstore`, `general`, `marketing`, `portrait`, `commercial`.
- `--ratio`: general mode ratio such as `1:1`, `9:16`, `16:9`.
- `--template`: template id for marketing/portrait/commercial modes.
- `--device`: AppStore device id.
- `--size`: `1K`, `2K`, or `4K`.
- `--grid`: batch grid such as `2x3`, `3x3`, `5x5`, `6x6`.
- `--count`: expected output count; the grid controls layout.
- `--reference`: reference image URL/data URL/local path; repeatable.
- `--api-key`: provider API key. Defaults to `GRSAI_API_KEY`.
- `--base-url`: custom provider base URL. Defaults to `GRSAI_BASE_URL` or `https://grsaiapi.com`.
- `--domestic-base-url`: custom domestic base URL. Defaults to `GRSAI_DOMESTIC_BASE_URL`.
- `--draw-url`: full custom Banana draw endpoint. Defaults to `GRSAI_DRAW_URL` or `<base-url>/v1/draw/nano-banana`.
- `--gpt-image2-draw-url`: full custom GPT Image2 draw endpoint. Defaults to `GRSAI_GPT_IMAGE2_DRAW_URL` or `<base-url>/v1/draw/completions`.
- `--result-url`: full custom polling endpoint. Defaults to `GRSAI_RESULT_URL` or `<base-url>/v1/draw/result`.
- `--save-raw`: also save the provider's raw composite image.

Dependencies:

- Python 3.
- Pillow (`PIL`) for local resize and splitting.
- Network/API key only when not using `--dry-run`.

## Original Project Shape

Default project path:

```bash
/Users/jiangfei/OpenAI/screenshot-studio-pro
```

Main files:

- `src/App.tsx`: primary UI state, scene selection, output count UI, generate payload.
- `src/services/api.ts`: orchestration for sizing, prompt building, provider call, batch split, carousel split, strict resize.
- `src/services/config.ts`: providers, endpoints, device sizes, general ratios, marketing/portrait/commercial templates.
- `src/services/promptBuilder.ts`: prompt guardrails, layout rules, batch grid prompt.
- `src/services/providers/grsai.ts`: Grsai direct browser provider, including Banana and GPT Image2 request bodies.
- `functions/api/generate.js`: Cloudflare Pages backend proxy mirroring Grsai/Gemini request logic.
- `src/utils/grid.ts`: Banana 4K canvas sizes, tiered dimensions, allowed output grid rules, feasibility checks.
- `src/utils/modelCapabilities.ts`: provider/model feature gates such as GPT Image2 single-image behavior.
- `src/cli/index.ts`: CLI entrypoint, but browser canvas post-processing is more complete than CLI.

## Original Project Commands

Use these only when maintaining or testing the original React app from the project root:

```bash
npm run dev
npm run lint
npm run build
npm run cli:list-devices
npm run cli:list-providers
```

Use the in-app browser for localhost testing only when UI behavior matters:

```text
http://localhost:3000/
```

Prefer `npm run lint` and `npm run build` after app edits. `npm run dev` runs on port 3000.

## Scene Modes

Use these modes when constructing or debugging payloads:

- `appstore`: App Store screenshots and store assets. Uses device sizes such as iPhone 6.5, iPad, app icon, Google Play, Steam, Chrome promo. AppStore mode must preserve exact final device pixels.
- `general`: freeform aspect ratios from `GENERAL_RATIOS`, scaled by 1K/2K/4K.
- `marketing`: YouTube banner, OG image, IG story, webtoon, 2/4-slide carousel.
- `portrait`: business headshot, glamour portrait, passport photo.
- `commercial`: product poster, luxury showcase, ecommerce main image.

## Provider And Model Rules

### Banana through Grsai

Banana-like models use:

```json
{
  "model": "nano-banana",
  "prompt": "...",
  "aspectRatio": "1:1",
  "imageSize": "2K",
  "webHook": "-1",
  "shutProgress": false,
  "urls": []
}
```

Important behavior:

- Send `aspectRatio` from canvas width/height via `convertSizeToAspectRatio`.
- Send `imageSize` for Banana unless unavailable; batch usually forces provider canvas to `4K`.
- Domestic endpoint may be used for Banana when enabled.
- Poll `/v1/draw/result` until success.

### GPT Image2 through Grsai

GPT Image2 must not receive Banana's `aspectRatio` or `imageSize` schema. Use the Grsai completions endpoint:

```json
{
  "size": "auto",
  "prompt": "...",
  "urls": [],
  "badPrompt": "",
  "model": "gpt-image-2",
  "webHook": "",
  "shutProgress": false,
  "variants": 1,
  "cdn": ""
}
```

Important behavior:

- Use `/v1/draw/completions`.
- Force `size: "auto"` and `variants: 1`.
- Disable domestic endpoint.
- Treat as single-image generation. Do not expose Banana batch grids for GPT Image2.
- Use prompt geometry guidance and local strict resize for final target dimensions.

### Gemini

Gemini provider exists, but current Grsai/Banana/GPT Image2 behavior is the primary production path. Verify Gemini separately if relying on it because provider SDK and model names can change.

## Sizing Rules

Use `getTieredDimensions(baseWidth, baseHeight, tier)`:

- `1K`: scale longest side to 1024.
- `2K`: scale longest side to 2048.
- `4K`: snap to closest supported Banana 4K canvas ratio from `BANANA_4K_SIZES`.

Never assume a selected 2K batch means sending `2K * rows/cols` directly to the provider. The stable pattern is:

1. Calculate the per-output target size.
2. Calculate grid shape.
3. Snap the full grid to a provider-friendly 4K canvas.
4. Generate one grid image.
5. Split into cells.
6. Resize each cell back to the target output size.

For AppStore, preserve final exact device pixels. For general/marketing/portrait/commercial, preserve selected tier output dimensions after slicing.

## Output Quantity Rules

Only expose output quantities that are stable for slicing:

- Always allow `1`.
- Allow any even total count.
- Allow square grids such as `3x3`, `5x5`, `6x6`.
- Do not allow non-square odd grids such as `1x3`.
- Do not allow 3-slide carousel slicing.

Common UI grid options:

```text
1x1=1
1x2=2
2x2=4
2x3=6
2x4=8
3x3=9
3x4=12
4x4=16
4x5=20
4x6=24
5x5=25
4x8=32
6x6=36
6x8=48
```

Unsupported-but-valid-looking grids should be visible but disabled if they exceed model/canvas feasibility. Do not silently generate them.

## Batch Prompt Requirements

When batch mode is enabled, the prompt must explicitly constrain the grid:

- State exact rows, columns, and total cells.
- Require equal cells and exact dividing lines.
- Forbid extra images, bonus panels, title cards, inset previews, and partial extra cells.
- For AppStore cells, require each cell to be a full device graphic and have its own status bar if applicable.
- Treat instructions as hidden production guidance; never render prompt text, measurements, labels, debug overlays, crop marks, or aspect-ratio notation unless explicitly requested as visible UI text.

If the provider output contains the wrong number of cells, prefer fixing prompt and grid feasibility before changing split math.

## Local Post-Processing

Browser path:

- `splitGridImageAsync(imageUrl, rows, cols, targetWidth, targetHeight)` splits grid images and resizes each cell.
- `resizeImageStrict(imageUrl, targetWidth, targetHeight)` object-fit-covers and exports a data URL.
- `fetchAndResizeThroughProxy` handles CORS failures via `/api/proxy-image`.

Safety checks:

- Split only when `batchMode` is true and `gridSize` passes `isAllowedOutputGridSize`.
- For carousel slicing, reject odd slide counts unless deliberately re-enabled.
- Keep target widths/heights explicit when exact final dimensions matter.

## Reference Images

Reference images can be URLs or data URLs:

- Grsai sends references as `urls`.
- Gemini sends data URLs as inline data.
- The UI limits reference image uploads to 4.
- Add `getReferenceInstruction` when references are present.

When using local files through CLI or future scripts, convert to data URL if the provider requires inline image data.

## Agent Workflow

When asked to generate, debug, or extend a workflow:

1. Inspect the current selected provider/model and scene mode.
2. Prefer `scripts/studio_generate.py` for direct generation. Only use the React app when the user asks to inspect UI behavior.
3. Use model rules to decide fields:
   - Banana: `aspectRatio` and `imageSize`.
   - GPT Image2: `size:auto`, no `aspectRatio`, no `imageSize`, single output.
4. Use grid rules to validate quantity.
5. Use sizing rules to compute provider canvas and final output dimensions.
6. Confirm prompt contains appropriate layout and hidden-instruction guardrails.
7. Use `--dry-run` before real network calls when constructing unfamiliar requests.
8. Run `npm run lint` and `npm run build` after original app code changes.
9. If UI changed, open or refresh `http://localhost:3000/` in the in-app browser.

## Debugging Checklist

For provider errors:

- Log or inspect the actual request body.
- Compare GPT Image2 body against the exact `size:auto` schema above.
- Confirm GPT Image2 uses `/v1/draw/completions`.
- Confirm Banana uses `/v1/draw/nano-banana`.
- Confirm domestic endpoint is disabled for GPT Image2.

For wrong output count:

- Check `config.gridSize`, `batchMode`, `getExpectedOutputCount`, and `isAllowedOutputGridSize`.
- Ensure UI list, payload grid, prompt rows/cols, and split rows/cols match.
- Check whether the model drew extra panels; strengthen the batch prompt if so.

For wrong dimensions:

- Check `getTieredDimensions`.
- Check provider canvas dimensions versus final slice target dimensions.
- Check whether strict resize used `targetDeviceW/targetDeviceH`.

For inaccessible page:

- Verify `npm run dev` is running.
- Check `curl -I http://localhost:3000/`.
- If build succeeds but UI is stale, hard refresh the in-app browser.

## Editing Rules

When modifying this app:

- Keep frontend and backend Grsai schemas in sync: `src/services/providers/grsai.ts` and `functions/api/generate.js`.
- Keep UI model options in sync with `src/services/config.ts`.
- Keep UI quantity options in sync with `src/utils/grid.ts`.
- Do not add model capabilities only in UI; enforce them in `generateImage`.
- Do not add output quantities only in UI; enforce them before prompt building and splitting.
- Avoid destructive git commands.
- Preserve unrelated local changes.
