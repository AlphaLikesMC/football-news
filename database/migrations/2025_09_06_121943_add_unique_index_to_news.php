<?php
// database/migrations/xxxx_add_unique_index_to_news.php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void {
        Schema::table('news', function (Blueprint $table) {
            $table->unique('link');
        });
    }

    public function down(): void {
        Schema::table('news', function (Blueprint $table) {
            $table->dropUnique(['link']);
        });
    }
};

