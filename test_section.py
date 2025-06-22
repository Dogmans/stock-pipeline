if __name__ == "__main__":
    logger.info("Testing screeners module...")
    
    # Check if market is in correction
    in_correction, status = is_market_in_correction()
    logger.info(f"Market status: {status}")
    
    # Test various screeners
    logger.info("Testing book value screener...")
    book_value_stocks = screen_for_price_to_book(universe_df=config.UNIVERSES["SP500"])
    if not book_value_stocks.empty:
        logger.info(f"Found {len(book_value_stocks)} stocks trading near book value")
        save_screener_results(book_value_stocks, "book_value_stocks.csv")
    
    logger.info("Testing PE ratio screener...")
    low_pe_stocks = screen_for_pe_ratio(universe_df=config.UNIVERSES["SP500"])
    if not low_pe_stocks.empty:
        logger.info(f"Found {len(low_pe_stocks)} stocks with low P/E ratios")
        save_screener_results(low_pe_stocks, "low_pe_stocks.csv")
    
    logger.info("Testing 52-week low screener...")
    lows_52week_stocks = screen_for_52_week_lows(universe_df=config.UNIVERSES["SP500"])
    if not lows_52week_stocks.empty:
        logger.info(f"Found {len(lows_52week_stocks)} stocks near 52-week lows")
        save_screener_results(lows_52week_stocks, "52week_low_stocks.csv")
      logger.info("Testing sector correction screener...")
    sector_corrections = screen_for_sector_corrections(universe_df=get_stock_universe(config.UNIVERSES["SP500"]))
    if not sector_corrections.empty:
        unique_sectors = len(sector_corrections['sector'].unique()) if 'sector' in sector_corrections.columns else 0
        logger.info(f"Found {len(sector_corrections)} stocks in {unique_sectors} sectors in correction")
        save_screener_results(sector_corrections, "sector_corrections.csv")
    
    logger.info("Testing combined screener...")
    combined_results = combine_screeners(universe_df=config.UNIVERSES["SP500"])
    if not combined_results.empty:
        logger.info(f"Found {len(combined_results)} stocks in combined screener")
        logger.info(f"Top 5 stocks by score: {combined_results.head(5)['symbol'].tolist()}")
        save_screener_results(combined_results, "combined_results.csv")
    
    logger.info("Screener tests complete")
