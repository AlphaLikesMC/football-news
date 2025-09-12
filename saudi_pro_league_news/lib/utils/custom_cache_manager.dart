import 'package:flutter_cache_manager/flutter_cache_manager.dart';

class CustomCacheManager {
  static const key = 'newsAppCache';

  // A simple shared CacheManager with reasonable defaults for news thumbnails
  static final CacheManager instance = CacheManager(
    Config(
      key,
      stalePeriod: const Duration(days: 7), // keep cached images for 7 days
      maxNrOfCacheObjects: 200, // up to 200 files
      repo: JsonCacheInfoRepository(databaseName: key),
      fileService: HttpFileService(),
    ),
  );
}
