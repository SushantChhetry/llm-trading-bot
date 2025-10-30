# Quick Installation Guide

## Option 1: Standard Installation (Recommended)

Install all dependencies using npm:

```bash
# Install dependencies
npm install
```

## Option 2: Manual Installation

If you want to install step by step:

```bash
# Install core React dependencies
npm install react react-dom

# Install charting library
npm install recharts

# Install UI utilities
npm install clsx tailwind-merge class-variance-authority

# Install icons
npm install lucide-react

# Install minimal Radix components
npm install @radix-ui/react-separator @radix-ui/react-slot

# Install dev dependencies
npm install -D @types/react @types/react-dom typescript vite @vitejs/plugin-react
npm install -D tailwindcss postcss autoprefixer
npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
```

## Option 3: Use the Setup Script

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

## After Installation

1. **Start the API server** (Terminal 1):
   ```bash
   python api_server.py
   ```

2. **Start the React app** (Terminal 2):
   ```bash
   npm run dev
   ```

3. **Open your browser** to: http://localhost:3000

## Troubleshooting

### If you get Radix UI errors:
- Try installing dependencies one by one using Option 2 above
- The dashboard will work without all Radix components

### If you get TypeScript errors:
- Make sure you have TypeScript installed: `npm install -D typescript`
- Check that your tsconfig.json is correct

### If you get Tailwind CSS errors:
- Make sure Tailwind is installed: `npm install -D tailwindcss postcss autoprefixer`
- Run: `npx tailwindcss init -p`

## What's Included

The dashboard includes:
- ✅ React + Vite
- ✅ Recharts for graphs
- ✅ Tailwind CSS for styling
- ✅ Lucide React for icons
- ✅ Radix UI components for advanced UI elements
- ✅ TypeScript support
- ✅ WebSocket support for real-time updates

The dashboard provides a comprehensive trading bot monitoring interface!
