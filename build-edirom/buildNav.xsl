<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="xs" version="2.0">

    <xsl:output indent="yes" />
    <xsl:param name="properties" select="document('../properties.xml')" />
    
    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="node()|@*"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="navigatorCategory">
        <xsl:variable name="catPos" select="count(preceding-sibling::navigatorCategory) + 1"/>
        <navigatorCategory xml:id="navCategory-{$catPos}">
            <xsl:apply-templates select="@*|node()"/>
        </navigatorCategory>
    </xsl:template>
    
    <xsl:template match="navigatorItem">
        <xsl:variable name="navCatPos" select="count(ancestor::navigatorCategory/preceding-sibling::navigatorCategory) + 1"/>
        <xsl:variable name="itemPos" select="count(preceding-sibling::navigatorItem) + 1"/>
        <navigatorItem xml:id="navItem-{$navCatPos}-{$itemPos}" sortNo="{$itemPos}" targets="xmldb:exist:///db/apps/edirom-content/{$properties//property[@name='editionHandle']}/{./@targets}">
            <xsl:apply-templates select="@*[name() != 'targets']|node()"/>
        </navigatorItem>
    </xsl:template>
    
</xsl:stylesheet>