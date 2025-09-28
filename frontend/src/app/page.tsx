"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  Loader2,
  ShoppingBag,
  Globe,
  Sparkles,
  Copy,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

// Types
interface AnalysisResult {
  title: string;
  description: string;
  tags: string[];
}

interface ApiResponse {
  success: boolean;
  data?: AnalysisResult;
  error?: string;
}

// Supported languages
const SUPPORTED_LANGUAGES = {
  English: "en",
  "ไทย (Thai)": "th",
  "中文 (Chinese)": "zh",
  "日本語 (Japanese)": "ja",
  "한국어 (Korean)": "ko",
  "Español (Spanish)": "es",
  "Français (French)": "fr",
  "Deutsch (German)": "de",
  "Italiano (Italian)": "it",
  "Português (Portuguese)": "pt",
  "Русский (Russian)": "ru",
  "العربية (Arabic)": "ar",
};

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("en");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      setResult(null);

      // Create image preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("language", selectedLanguage);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/generate-product-info`, {
        method: "POST",
        body: formData,
      });

      // Handle HTTP error responses
      if (!response.ok) {
        if (response.status === 429) {
          const errorData = await response.json().catch(() => ({}));
          setError(
            errorData.detail ||
              "API quota exceeded. Please try again later or upgrade your plan."
          );
          return;
        } else if (response.status === 503) {
          setError(
            "Service temporarily unavailable. Please try again in a moment."
          );
          return;
        } else {
          const errorData = await response.json().catch(() => ({}));
          setError(errorData.detail || `Server error: ${response.status}`);
          return;
        }
      }

      const data: ApiResponse = await response.json();

      if (data.success && data.data) {
        setResult(data.data);
      } else {
        setError(data.error || "Analysis failed");
      }
    } catch (err) {
      console.error("API Error:", err);

      // Check if it's a network error or server error
      if (err instanceof TypeError && err.message.includes("fetch")) {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        setError(
          `Failed to connect to the API server. Make sure the FastAPI server is running on ${apiUrl}`
        );
      } else {
        setError(
          "An unexpected error occurred. Please try again or check the server logs."
        );
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;

    const copyText = `**Title:** ${result.title}

**Description:** ${result.description}

**Tags:** ${result.tags.join(", ")}`;

    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center space-x-3">
            <ShoppingBag className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-bold text-foreground">
              AI Product Listing Assistant
            </h1>
          </div>
          <p className="text-center text-muted-foreground mt-2">
            Generate professional product listings from images using AI
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="space-y-6">
            <Card data-testid="upload-card">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Upload className="h-5 w-5" />
                  <span>Upload Product Image</span>
                </CardTitle>
                <CardDescription>
                  Upload a clear image of your product for best results
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Language Selection */}
                <div className="space-y-2">
                  <Label
                    htmlFor="language"
                    className="flex items-center space-x-2"
                  >
                    <Globe className="h-4 w-4" />
                    <span>Select Language</span>
                  </Label>
                  <Select
                    value={selectedLanguage}
                    onValueChange={setSelectedLanguage}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose language" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(SUPPORTED_LANGUAGES).map(
                        ([name, code]) => (
                          <SelectItem key={code} value={code}>
                            {name}
                          </SelectItem>
                        )
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {/* File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="file">Image File</Label>
                  <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center hover:border-muted-foreground/50 transition-colors">
                    <Input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="file-upload"
                    />
                    <Button
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      className="mb-2"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Image
                    </Button>
                    <p className="text-sm text-muted-foreground">
                      Supports PNG, JPG, JPEG, WebP, GIF
                    </p>
                  </div>
                </div>

                {/* Image Preview */}
                {imagePreview && (
                  <div className="space-y-2">
                    <Label>Image Preview</Label>
                    <div className="relative rounded-lg overflow-hidden border">
                      <Image
                        src={imagePreview}
                        alt="Product preview"
                        width={400}
                        height={300}
                        className="w-full h-64 object-cover"
                      />
                    </div>
                    {selectedFile && (
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>
                          <strong>Filename:</strong> {selectedFile.name}
                        </p>
                        <p>
                          <strong>Size:</strong>{" "}
                          {(selectedFile.size / 1024).toFixed(1)} KB
                        </p>
                        <p>
                          <strong>Type:</strong> {selectedFile.type}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Analyze Button */}
                <Button
                  onClick={handleAnalyze}
                  disabled={!selectedFile || isAnalyzing}
                  className="w-full"
                  size="lg"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Analyze Product
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Results Section */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Sparkles className="h-5 w-5" />
                  <span>Analysis Results</span>
                </CardTitle>
                <CardDescription>
                  AI-generated product listing content
                </CardDescription>
              </CardHeader>
              <CardContent>
                {error && (
                  <div className="flex items-center space-x-2 p-4 border border-destructive/50 rounded-lg bg-destructive/10">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <p className="text-sm text-destructive">{error}</p>
                  </div>
                )}

                {result && (
                  <div className="space-y-4">
                    {/* Title */}
                    <div className="space-y-2">
                      <Label className="text-base font-semibold">
                        Product Title
                      </Label>
                      <div className="p-3 bg-muted rounded-lg">
                        <p className="font-medium">{result.title}</p>
                      </div>
                    </div>

                    {/* Description */}
                    <div className="space-y-2">
                      <Label className="text-base font-semibold">
                        Product Description
                      </Label>
                      <div className="p-3 bg-muted rounded-lg">
                        <p>{result.description}</p>
                      </div>
                    </div>

                    {/* Tags */}
                    <div className="space-y-2">
                      <Label className="text-base font-semibold">
                        Product Tags
                      </Label>
                      <div className="flex flex-wrap gap-2">
                        {result.tags.map((tag, index) => (
                          <Badge key={index} variant="secondary">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {/* Copy Button */}
                    <Button
                      onClick={handleCopy}
                      variant="outline"
                      className="w-full"
                    >
                      {copied ? (
                        <>
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy All Content
                        </>
                      )}
                    </Button>

                    {/* Copy-friendly format */}
                    <div className="space-y-2">
                      <Label className="text-base font-semibold">
                        Copy-Friendly Format
                      </Label>
                      <Textarea
                        value={`**Title:** ${result.title}

**Description:** ${result.description}

**Tags:** ${result.tags.join(", ")}`}
                        readOnly
                        className="min-h-[120px]"
                      />
                    </div>
                  </div>
                )}

                {!result && !error && !isAnalyzing && (
                  <div className="text-center py-8">
                    <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">
                      Upload an image to start the analysis
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 mt-16">
        <div className="container mx-auto px-4 py-6">
          <p className="text-center text-muted-foreground">
            Made with ❤️ for e-commerce sellers worldwide | Powered by Google
            Gemini AI
          </p>
        </div>
      </footer>
    </div>
  );
}
