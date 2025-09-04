<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Models\News;

Route::get('/news', function (Request $request) {
    return News::orderBy('published_at', 'desc')->paginate(20);
});


#Route::get('/news', [NewsController::class, 'index']);
#Route::get('/news/{id}', [NewsController::class, 'show']);

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

