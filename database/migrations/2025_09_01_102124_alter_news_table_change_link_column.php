<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up()
    {
        Schema::table('news', function (Blueprint $table) {
            $table->text('link')->change();
        });
    }

    public function down()
    {
        Schema::table('news', function (Blueprint $table) {
            $table->string('link', 255)->change();
        });
    }
};
