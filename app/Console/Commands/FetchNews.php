<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use App\Models\News;

class FetchNews extends Command
{
    protected $signature = 'fetch:news {--since=}';
    protected $description = 'Fetch Saudi Pro League related football news (with categories)';

    public function handle()
    {
        $this->info("🔍 Fetching articles from Python microservice...");

        try {
            $base = "https://airy-harmony-production-31f6.up.railway.app:5000/saudi-news";

            // Optional delta fetch: --since="2025-01-01 00:00:00" or "2025-01-01"
            $since = $this->option('since');
            $url = $since ? $base . '?since=' . urlencode($since) : $base;

            $response = Http::timeout(120)->get($url);

            if (!$response->successful()) {
                $this->error("⚠️ Failed to reach Python service: ".$response->status());
                return;
            }

            $articles = $response->json();
            $imported = 0;

            foreach ($articles as $article) {
                $title   = $article['title'] ?? '';
                $content = $article['content'] ?? '';
                $link    = $article['link'] ?? '';

                if (!$title || !$link) {
                    continue;
                }

                // Skip suspicious/bot-blocked responses
                $blob = strtolower($title . ' ' . $content);
                if (str_contains($blob, '429 too many requests') ||
                    str_contains($blob, 'access denied') ||
                    str_contains($blob, 'captcha') ||
                    str_contains($blob, 'cloudflare')) {
                    continue;
                }

                News::updateOrCreate(
                    ['link' => $link],
                    [
                        'title'        => $title,
                        'description'  => $article['description'] ?? null,
                        'published_at' => $article['published_at'] ?? now()->toDateTimeString(),
                        'content'      => $content ?: null,
                        'image'        => !empty($article['image']) ? $article['image'] : null,
                        'category'     => $article['category'] ?? 'General',
                    ]
                );

                $imported++;
            }

            $this->info("✅ Imported/Updated {$imported} of ".count($articles)." items.");
        } catch (\Exception $e) {
            $this->error("❌ Error: " . $e->getMessage());
        }
    }
}
