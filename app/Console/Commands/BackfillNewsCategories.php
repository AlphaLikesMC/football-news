<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\News;

class BackfillNewsCategories extends Command
{
    protected $signature = 'news:backfill-categories';
    protected $description = 'Assign categories to news articles without a category';

    public function handle()
    {
        $this->info("🔄 Backfilling categories...");

        $updated = 0;

        // Fetch all rows missing category
        $articles = News::whereNull('category')
            ->orWhere('category', '')
            ->get();

        foreach ($articles as $article) {
            $category = $this->detectCategory($article->title, $article->content ?? '');

            if ($category) {
                $article->category = $category;
                $article->save();
                $updated++;
            }
        }

        $this->info("✅ Backfilled $updated articles with categories.");
    }

    private function detectCategory(string $title, string $content): string
    {
        $text = strtolower($title . ' ' . $content);

        if (preg_match('/transfer|signing|loan|deal|contract/', $text)) {
            return "Transfer News";
        }
        if (preg_match('/injury|fitness|medical/', $text)) {
            return "Injury Update";
        }
        if (preg_match('/match report|full-time|kick-off|lineup/', $text)) {
            return "Match Report";
        }

        return "General";
    }
}
