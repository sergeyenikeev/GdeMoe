package com.gdemo.data.repository

import com.gdemo.data.model.Item
import com.gdemo.data.model.LocationNode

class ItemRepository {
    fun demoItems(): List<Item> = listOf(
        Item(id = 1, title = "Перфоратор Bosch", status = "ok", location = "Дом / Шкаф 2"),
        Item(id = 2, title = "Пылесос Dyson", status = "ok", location = "Гостиная", needsReview = true),
        Item(id = 3, title = "Набор бит 128 шт", status = "needs_review", location = "Гараж / Полка 2", needsReview = true)
    )

    fun demoLocations(): List<LocationNode> = listOf(
        LocationNode(
            id = "home1",
            name = "Дом",
            children = listOf(
                LocationNode(
                    id = "room1",
                    name = "Гостиная",
                    children = listOf(
                        LocationNode(
                            id = "closet1",
                            name = "Шкаф",
                            children = listOf(LocationNode("box1", "Коробка A1"))
                        )
                    )
                ),
                LocationNode(id = "garage", name = "Гараж", children = listOf(LocationNode("shelf2", "Полка 2")))
            )
        )
    )
}
