
    
  

    # Automatyczne uruchomienia działają tylko 08:00-22:00.
    # Ręczny "Run workflow" ma pusty GITHUB_EVENT_SCHEDULE,
    # więc może działać o dowolnej porze.
    if SCHEDULE and not (8 <= now.hour < 22):
        print(
            f"Poza godzinami monitoringu: "
            f"{now.strftime('%Y-%m-%d %H:%M')} Europe/Warsaw"
        )
        return

    if not SCHEDULE:
        print(
            f"TRYB RĘCZNY: ignoruję godziny monitoringu "
            f"({now.strftime('%Y-%m-%d %H:%M')} Europe/Warsaw)"
        )

    weekday = now.weekday()
    state = load_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/141.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        for hotel in HOTELS:
            if not should_check_hotel(hotel["id"], weekday):
                print(
                    f"{hotel['name']}: dzisiaj nie monitorujemy "
                    f"({now.strftime('%A')})."
                )
                continue

            try:
                result = check_hotel(page, hotel)

                price = result["price"]
                old_price = state.get(hotel["id"], {}).get("price")

                if old_price is None:
                    telegram(
                        "✅ CanWanBot rozpoczął obserwację\n\n"
                        + format_offer(hotel, result)
                        + f"\n\nPróg alarmu: {hotel['limit']:,} zł"
                    )

                elif (
                    price <= hotel["limit"]
                    and old_price > hotel["limit"]
                ):
                    telegram(
                        f"🔥🔥 MEGA OKAZJA 🔥🔥\n\n"
                        f"Było: {old_price:,} zł\n"
                        f"Teraz: {price:,} zł\n"
                        f"Spadek: {old_price-price:,} zł\n\n"
                        + format_offer(hotel, result)
                    )

                elif (
                    old_price is not None
                    and old_price - price >= DROP_ALERT
                ):
                    telegram(
                        f"📉 DUŻY SPADEK CENY\n\n"
                        f"Było: {old_price:,} zł\n"
                        f"Teraz: {price:,} zł\n"
                        f"Taniej o: {old_price-price:,} zł\n\n"
                        + format_offer(hotel, result)
                    )

                state[hotel["id"]] = {
                    "price": price,
                    "date": result["date"],
                    "airport": result["airport"],
                    "room": result["room"],
                    "board": result["board"],
                    "url": result["url"]
                }

            except Exception as e:
                print(
                    "BŁĄD",
                    hotel["name"],
                    ":",
                    repr(e)
                )

        browser.close()

    save_state(state)

    if SCHEDULE == "0 7 * * 1-5":
        thb = state.get("thb", {})
        dunas = state.get("dunas", {})

        telegram(
            "✅ CanWanBot działa\n\n"
            f"THB: {thb.get('price', '?')} zł\n"
            f"Dunas: {dunas.get('price', '?')} zł\n\n"
            "Zakres wylotu: do 17.11.2026"
        )


if __name__ == "__main__":
    main()

