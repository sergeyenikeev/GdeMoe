package com.gdemo.data.model

data class MediaUploadResponse(
    val id: Int,
    val path: String,
    val mime_type: String?,
    val size_bytes: Long? = null,
    val file_hash: String? = null,
    val thumb_path: String? = null,
    val analysis: MediaAnalysisDto? = null
)
