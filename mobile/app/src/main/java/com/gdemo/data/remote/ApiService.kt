package com.gdemo.data.remote

import com.gdemo.data.model.CreateItemRequest
import com.gdemo.data.model.Item
import com.gdemo.data.model.MediaDto
import com.gdemo.data.model.MediaUploadResponse
import com.gdemo.data.model.UpdateItemRequest
import com.gdemo.data.model.LocationDto
import com.gdemo.data.model.LocationCreateRequest
import com.gdemo.data.model.LocationUpdateRequest
import com.gdemo.data.model.ProductImportRequest
import com.gdemo.data.model.ProductImportResponse
import com.gdemo.data.model.ReceiptImportResponse
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.model.AiDetectionActionRequest
import com.gdemo.data.model.AiDetectionReviewLogRequest
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Multipart
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Headers
import retrofit2.Response

interface ApiService {
    @GET("/api/v1/health")
    suspend fun health(): Map<String, String>

    @GET("/api/v1/items")
    suspend fun items(): List<Item>

    @GET("/api/v1/locations")
    suspend fun locations(): List<LocationDto>

    @GET("/api/v1/locations/{id}/items")
    suspend fun itemsByLocation(@Path("id") id: Int): List<Item>

    @POST("/api/v1/locations")
    suspend fun createLocation(@Body body: LocationCreateRequest): LocationDto

    @PATCH("/api/v1/locations/{id}")
    suspend fun updateLocation(@Path("id") id: Int, @Body body: LocationUpdateRequest): LocationDto

    @DELETE("/api/v1/locations/{id}")
    suspend fun deleteLocation(@Path("id") id: Int): Response<Unit>

    @POST("/api/v1/imports/product-link")
    @Headers("Content-Type: application/json")
    suspend fun importProductLink(@Body body: ProductImportRequest): ProductImportResponse

    @Multipart
    @POST("/api/v1/imports/receipt")
    suspend fun importReceipt(
        @Part file: okhttp3.MultipartBody.Part,
        @Part("workspace_id") workspaceId: okhttp3.RequestBody,
        @Part("scope") scope: okhttp3.RequestBody
    ): ReceiptImportResponse

    @GET("/api/v1/items/{id}")
    suspend fun getItem(@Path("id") id: Int): Item

    @POST("/api/v1/items")
    suspend fun createItem(@Body body: CreateItemRequest): Item

    @GET("/api/v1/items/search")
    suspend fun searchItems(
        @Query("query") query: String = "",
        @Query("status") status: String? = null
    ): List<Item>

    @PATCH("/api/v1/items/{id}")
    suspend fun updateItem(@Path("id") id: Int, @Body body: UpdateItemRequest): Item

    @DELETE("/api/v1/items/{id}")
    suspend fun deleteItem(@Path("id") id: Int): Response<Unit>

    @GET("/api/v1/items/{id}/media")
    suspend fun itemMedia(@Path("id") id: Int): List<MediaDto>

    @POST("/api/v1/items/{id}/media/{mediaId}")
    suspend fun linkMedia(@Path("id") id: Int, @Path("mediaId") mediaId: Int): Map<String, Any>

    @DELETE("/api/v1/items/{id}/media/{mediaId}")
    suspend fun unlinkMedia(
        @Path("id") id: Int,
        @Path("mediaId") mediaId: Int,
        @Query("delete_file") deleteFile: Boolean = false
    ): Response<Unit>

    @Multipart
    @POST("/api/v1/media/upload")
    suspend fun uploadMedia(
        @Part file: okhttp3.MultipartBody.Part,
        @Part("workspace_id") workspaceId: okhttp3.RequestBody,
        @Part("owner_user_id") ownerUserId: okhttp3.RequestBody,
        @Part("media_type") mediaType: okhttp3.RequestBody,
        @Part("scope") scope: okhttp3.RequestBody,
        @Part("subdir") subdir: okhttp3.RequestBody,
        @Part("item_id") itemId: okhttp3.RequestBody? = null,
        @Part("location_id") locationId: okhttp3.RequestBody? = null,
        @Part("analyze") analyze: okhttp3.RequestBody? = null,
        @Part("source") source: okhttp3.RequestBody? = null,
        @Part("client_created_at") clientCreatedAt: okhttp3.RequestBody? = null,
        @Part("mime_type") mimeType: okhttp3.RequestBody? = null
    ): MediaUploadResponse

    @GET("/api/v1/media/recent")
    suspend fun recentMedia(@Query("scope") scope: String = "public"): List<MediaDto>

    @GET("/api/v1/media/{id}")
    suspend fun mediaDetails(@Path("id") id: Int): MediaDto

    @GET("/api/v1/ai/detections")
    suspend fun aiDetections(@Query("status") status: String = "pending"): List<AiDetectionDto>

    @POST("/api/v1/ai/detections/{id}/accept")
    suspend fun acceptDetection(
        @Path("id") id: Int,
        @Body body: AiDetectionActionRequest
    ): AiDetectionDto

    @POST("/api/v1/ai/detections/{id}/reject")
    suspend fun rejectDetection(
        @Path("id") id: Int,
        @Body body: AiDetectionActionRequest? = null
    ): AiDetectionDto

    @POST("/api/v1/ai/detections/{id}/review_log")
    suspend fun addDetectionLog(
        @Path("id") id: Int,
        @Body body: AiDetectionReviewLogRequest
    ): Map<String, String>
}
