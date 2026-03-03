<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" 
    xmlns="http://www.edirom.de/ns/1.3"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    version="1.0">

    <xsl:output indent="yes" />
    <xsl:param name="editionSlug"></xsl:param>
    
    <xsl:template match="@*|text()">
        <xsl:copy/>
    </xsl:template>
    
    <xsl:template match="processing-instruction()"/>
    
    <xsl:template match="*">
        <xsl:element name="{local-name()}" namespace="http://www.edirom.de/ns/1.3">
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="navigatorDefinition">
        <navigatorDefinition>
            <xsl:apply-templates select="@*|node()"/>
        </navigatorDefinition>
    </xsl:template>
    
    <xsl:template match="navigatorCategory">
        <xsl:variable name="catPos" select="count(preceding-sibling::navigatorCategory) + 1"/>
        <navigatorCategory>
            <xsl:attribute name="xml:id">navCategory-<xsl:value-of select="$catPos"/></xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </navigatorCategory>
    </xsl:template>
    
    <xsl:template match="navigatorItem">
        <xsl:variable name="navCatPos" select="count(ancestor::navigatorCategory/preceding-sibling::navigatorCategory) + 1"/>
        <xsl:variable name="itemPos" select="count(preceding-sibling::navigatorItem) + 1"/>
        <navigatorItem>
            <xsl:attribute name="xml:id">navItem-<xsl:value-of select="$navCatPos"/>-<xsl:value-of select="$itemPos"/></xsl:attribute>
            <xsl:attribute name="sortNo"><xsl:value-of select="$itemPos"/></xsl:attribute>
            <xsl:attribute name="targets">xmldb:exist:///db/apps/edirom-content/<xsl:value-of select="$editionSlug"/>/...</xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'targets']|node()"/>
        </navigatorItem>
    </xsl:template>
    
</xsl:stylesheet>