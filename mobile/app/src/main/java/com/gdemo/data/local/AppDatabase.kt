package com.gdemo.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.gdemo.data.local.dao.ItemDao
import com.gdemo.data.local.entity.ItemEntity

@Database(entities = [ItemEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun itemDao(): ItemDao
}
