<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\News;
use Illuminate\Http\Request;

class NewsController extends Controller
{
    // GET /api/news -> paginated news
    public function index(Request $request)
    {
        $pageSize = $request->get('page_size', 10); // default 10
        $news = News::orderBy('published_at', 'desc')
            ->paginate($pageSize, ['id', 'title', 'description', 'content', 'published_at', 'link', 'image']); 

        return response()->json($news);
    }

    // GET /api/news/{id} -> single news item
    public function show($id)
    {
        $news = News::findOrFail($id);

        return response()->json($news);
    }
}
