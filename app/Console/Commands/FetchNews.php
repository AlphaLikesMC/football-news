<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use App\Models\News;

class FetchNews extends Command
{
    protected $signature = 'fetch:news';
    protected $description = 'Fetch Saudi Pro League related football news only';

    public function handle()
    {
        $this->info("🔍 Fetching articles from Python microservice...");

        try {
            $response = Http::timeout(500)->get("http://127.0.0.1:5000/saudi-news");

            if (!$response->successful()) {
                $this->error("⚠️ Failed to reach Python service");
                return;
            }

            $articles = $response->json();

            foreach ($articles as $article) {
                News::updateOrCreate(
                    ['link' => $article['link']],
                    [
                        'title'        => $article['title'],
                        'description'  => $article['description'] ?? null,
                        'published_at' => $article['published_at'],
                        'content'      => $article['content'],
                        'image'        => !empty($article['image']) ? $article['image'] : null,
                    ]
                );                
            }

            $this->info("✅ Imported " . count($articles) . " articles.");
        } catch (\Exception $e) {
            $this->error("❌ Error: " . $e->getMessage());
        }
    }
}
