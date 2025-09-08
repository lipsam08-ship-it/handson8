# retail_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')
st.set_page_config(page_title="Retail Analytics Dashboard", layout="wide")

# Title
st.title("🛍️ Retail Analytics Dashboard")
st.markdown("Upload your retail dataset (CSV) to explore sales, customers, and trends.")

# File uploader
uploaded_file = st.file_uploader("📤 Upload your retail dataset (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        st.success("✅ Dataset loaded successfully!")

        # Show shape and preview
        st.write(f"**Dataset Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
        st.dataframe(df.head())

        # === DATA PREP ===
        # Convert OrderDate if exists
        if 'OrderDate' in df.columns:
            df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce')
            if df['OrderDate'].isna().all():
                st.warning("⚠️ 'OrderDate' column exists but could not parse any dates.")
            else:
                st.info("📅 'OrderDate' parsed successfully.")
        else:
            st.warning("⚠️ 'OrderDate' column not found — time-series charts disabled.")

        # Ensure numeric for these if present
        numeric_cols = ['Sales', 'Quantity', 'Profit', 'UnitPrice']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # === FILTERS ===
        st.sidebar.header("FilterWhere")
        df_filtered = df.copy()

        # Date filter (robust to single-date selection)
        if 'OrderDate' in df.columns and df['OrderDate'].notna().any():
            min_date = df['OrderDate'].min().date()
            max_date = df['OrderDate'].max().date()
            date_sel = st.sidebar.date_input(
                "📅 Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            if isinstance(date_sel, tuple) and len(date_sel) == 2:
                start_date, end_date = date_sel
            else:
                # If the widget returns a single date
                start_date = end_date = date_sel
            mask = (df['OrderDate'].dt.date >= start_date) & (df['OrderDate'].dt.date <= end_date)
            df_filtered = df_filtered[mask]

        # Category filter
        if 'Category' in df_filtered.columns:
            cat_options = df_filtered['Category'].dropna().unique()
            categories = st.sidebar.multiselect(
                "🛍️ Category",
                options=cat_options,
                default=cat_options
            )
            df_filtered = df_filtered[df_filtered['Category'].isin(categories)]

        # Region filter
        if 'Region' in df_filtered.columns:
            reg_options = df_filtered['Region'].dropna().unique()
            regions = st.sidebar.multiselect(
                "📍 Region",
                options=reg_options,
                default=reg_options
            )
            df_filtered = df_filtered[df_filtered['Region'].isin(regions)]

        # === KPIs ===
        st.subheader("📈 Key Performance Indicators")
        total_sales = df_filtered['Sales'].sum() if 'Sales' in df_filtered.columns else 0
        total_orders = df_filtered['OrderID'].nunique() if 'OrderID' in df_filtered.columns else len(df_filtered)
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        total_profit = df_filtered['Profit'].sum() if 'Profit' in df_filtered.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sales", f"${total_sales:,.2f}")
        col2.metric("Total Orders", f"{total_orders:,}")
        col3.metric("Avg Order Value", f"${avg_order_value:,.2f}")
        col4.metric("Total Profit", f"${total_profit:,.2f}")

        # === INSIGHTS ===
        st.subheader("💡 Smart Insights")
        insights = []

        if 'Region' in df_filtered.columns and 'Sales' in df_filtered.columns:
            region_sales = df_filtered.groupby('Region', dropna=True)['Sales'].sum()
            if not region_sales.empty:
                top_region = region_sales.idxmax()
                insights.append(f"🏆 Top region: **{top_region}** with ${region_sales.max():,.2f} sales")

        if 'Category' in df_filtered.columns and 'Sales' in df_filtered.columns:
            cat_sales_s = df_filtered.groupby('Category', dropna=True)['Sales'].sum()
            if not cat_sales_s.empty:
                top_cat = cat_sales_s.idxmax()
                insights.append(f"🔥 Top category: **{top_cat}**")

        if 'OrderDate' in df_filtered.columns and 'Sales' in df_filtered.columns:
            df_time_tmp = df_filtered.dropna(subset=['OrderDate']).copy()
            if not df_time_tmp.empty:
                sales_over_time = (df_time_tmp
                                   .set_index('OrderDate')
                                   .sort_index()
                                   .resample('M')['Sales']
                                   .sum())
                if len(sales_over_time) > 1:
                    if sales_over_time.iloc[-1] > sales_over_time.iloc[-2]:
                        insights.append("📈 Sales are increasing recently")
                    else:
                        insights.append("📉 Sales are declining recently")

        for i, insight in enumerate(insights, 1):
            st.markdown(f"{i}. {insight}")

        # === GRAPHS SECTION ===
        st.subheader("📊 Data Visualizations")

        # 1. Sales Over Time (use DataFrame for Plotly)
        if 'OrderDate' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("📅 Sales Over Time", expanded=True):
                df_time = df_filtered.dropna(subset=['OrderDate']).copy()
                if not df_time.empty:
                    daily = (df_time
                             .set_index('OrderDate')
                             .sort_index()
                             .resample('D')['Sales']
                             .sum()
                             .reset_index())
                    daily.rename(columns={'OrderDate': 'Date', 'Sales': 'Sales'}, inplace=True)
                    fig1 = px.line(daily, x='Date', y='Sales', title='Daily Sales Trend')
                    fig1.update_layout(xaxis_title="Date", yaxis_title="Sales ($)")
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.warning("No valid data to plot sales over time.")

        # 2. Top Products (ensure DataFrame for Plotly)
        if 'Product' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("🏆 Top 10 Products by Sales", expanded=True):
                top_products = (df_filtered
                                .groupby('Product', dropna=True)['Sales']
                                .sum()
                                .sort_values(ascending=False)
                                .head(10)
                                .reset_index())
                if not top_products.empty:
                    fig2 = px.bar(
                        top_products,
                        x='Product',
                        y='Sales',
                        title='Top 10 Products by Sales',
                        labels={'Product': 'Product', 'Sales': 'Sales ($)'}
                    )
                    fig2.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.warning("No product sales data to display.")

        # 3. Sales by Category (ensure DataFrame for Plotly)
        if 'Category' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("🥧 Sales by Category", expanded=True):
                cat_sales = (df_filtered
                             .groupby('Category', dropna=True)['Sales']
                             .sum()
                             .reset_index())
                if not cat_sales.empty:
                    fig3 = px.pie(cat_sales, names='Category', values='Sales', title='Sales Distribution by Category')
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.warning("No category sales data.")

        # 4. Sales by Region (already a DataFrame)
        if 'Region' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("📍 Sales by Region", expanded=True):
                reg_sales = (df_filtered
                             .groupby('Region', dropna=True)['Sales']
                             .sum()
                             .reset_index())
                if not reg_sales.empty:
                    fig4 = px.bar(reg_sales, x='Region', y='Sales', title='Sales by Region', color='Region')
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.warning("No region sales data.")

        # 5. Correlation Heatmap
        numeric_df = df_filtered.select_dtypes(include='number')
        if len(numeric_df.columns) > 1:
            with st.expander("🔗 Correlation Heatmap", expanded=True):
                corr = numeric_df.corr(numeric_only=True)
                if not corr.empty:
                    fig5, ax = plt.subplots(figsize=(6, 4))
                    sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, ax=ax, fmt='.2f')
                    st.pyplot(fig5)
                else:
                    st.warning("Not enough numeric data for correlation.")

        # === DOWNLOADS ===
        st.subheader("💾 Download Report")

        summary_df = pd.DataFrame({
            "Metric": ["Total Sales", "Total Orders", "Avg Order Value", "Total Profit"],
            "Value": [f"${total_sales:,.2f}", f"{total_orders:,}", f"${avg_order_value:,.2f}", f"${total_profit:,.2f}"]
        })
        csv = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Summary", data=csv, file_name="summary.csv", mime="text/csv")

        # TXT Report via download_button (simpler & reliable on Cloud)
        if st.button("📄 Generate Text Report (.txt)"):
            report_lines = [
                "==================================",
                "    RETAIL ANALYTICS REPORT",
                "==================================",
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "----- KEY METRICS -----",
                f"Total Sales      : ${total_sales:,.2f}",
                f"Total Orders     : {total_orders:,}",
                f"Avg Order Value  : ${avg_order_value:,.2f}",
                f"Total Profit     : ${total_profit:,.2f}",
                "",
                "----- INSIGHTS -----",
            ]
            report_lines.extend([f"{i+1}. {ins}" for i, ins in enumerate(insights)])
            report_lines.append("\n----- END OF REPORT -----")
            txt_data = "\n".join(report_lines).encode('utf-8')

            # Use download_button instead of a manual data URL
            st.download_button(
                "⬇️ Download TXT Report",
                data=txt_data,
                file_name="Retail_Report.txt",
                mime="text/plain"
            )

        # Raw data
        if st.checkbox("Show Raw Data"):
            st.dataframe(df_filtered)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.code(e)
else:
    st.info("👈 Please upload a CSV file to begin.")

# Footer
st.markdown("---")
st.markdown("📊 Retail Analytics Dashboard | Built with ❤️ Streamlit")
