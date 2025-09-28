# AI Product Listing Assistant - Next.js Frontend

A modern, responsive Next.js frontend for the AI Product Listing Assistant, built with shadcn/ui components and the Scaled theme.

## 🚀 Features

- **Modern UI**: Built with Next.js 15, React 18, and TypeScript
- **shadcn/ui Components**: Professional, accessible UI components with consistent theming
- **Responsive Design**: Works seamlessly across desktop, tablet, and mobile devices
- **Multi-language Support**: Generate product listings in 12 different languages
- **Image Upload**: Drag-and-drop file upload with preview functionality
- **Real-time Analysis**: Connect to FastAPI backend for AI-powered product analysis
- **Copy-friendly Output**: Easy-to-copy formatted results for e-commerce platforms
- **Error Handling**: Comprehensive error states and user feedback
- **Accessibility**: WCAG compliant with proper ARIA labels and keyboard navigation

## 🛠 Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Scaled theme)
- **Icons**: Lucide React
- **Testing**: Playwright (E2E testing)
- **Package Manager**: npm

## 📦 Installation

1. **Navigate to the frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Install Playwright browsers (for testing):**
   ```bash
   npx playwright install
   ```

## 🏃‍♂️ Running the Application

### Development Mode

Start the development server:

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### Production Build

Build for production:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## 🧪 Testing

### Run Playwright Tests

Run all tests:

```bash
npx playwright test
```

Run tests with browser UI (headed mode):

```bash
npx playwright test --headed
```

Run tests for specific browser:

```bash
npx playwright test --project=chromium
```

View test report:

```bash
npx playwright show-report
```

### Test Coverage

The test suite includes:

- ✅ **UI Component Tests**: Verify shadcn/ui components load correctly
- ✅ **Responsive Design Tests**: Test across desktop, tablet, and mobile viewports
- ✅ **Theme Tests**: Validate Scaled theme styling and CSS loading
- ✅ **Integration Tests**: Check API connectivity and error handling
- ✅ **Cross-browser Tests**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari

## 🎨 UI Components

The frontend uses shadcn/ui components with the Scaled theme:

- **Button**: Primary actions and file upload triggers
- **Card**: Content containers for upload and results sections
- **Input**: File upload and form inputs
- **Label**: Accessible form labels
- **Select**: Language selection dropdown
- **Textarea**: Copy-friendly formatted output
- **Badge**: Product tags display
- **Icons**: Lucide React icons for visual enhancement

## 🌐 API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`:

### Endpoints Used:

- `POST /generate-product-info`: Upload image and generate product listing

### Request Format:

```typescript
FormData {
  file: File,
  language: string
}
```

### Response Format:

```typescript
{
  success: boolean,
  data?: {
    title: string,
    description: string,
    tags: string[]
  },
  error?: string
}
```

## 🌍 Supported Languages

The application supports 12 languages:

- English (en)
- ไทย Thai (th)
- 中文 Chinese (zh)
- 日本語 Japanese (ja)
- 한국어 Korean (ko)
- Español Spanish (es)
- Français French (fr)
- Deutsch German (de)
- Italiano Italian (it)
- Português Portuguese (pt)
- Русский Russian (ru)
- العربية Arabic (ar)

## 📱 Responsive Design

The application is fully responsive with breakpoints:

- **Mobile**: < 768px (single column layout)
- **Tablet**: 768px - 1024px (adaptive layout)
- **Desktop**: > 1024px (two-column layout)

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file for local development:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Tailwind Configuration

The application uses a custom Tailwind configuration with shadcn/ui integration. See `tailwind.config.ts` for details.
